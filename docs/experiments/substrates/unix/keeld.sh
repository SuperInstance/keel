#!/bin/sh
# shellcheck disable=SC2039
# keeld.sh — The Keel Daemon
# Manages the keel process tree. The daemon itself is just a process.
# No central authority. Every component is a process that can die.
# The daemon's job: lay the runtime directory, relay signals, clean the dead.
#
# Philosophy:
#   The daemon doesn't _control_ agents. It _observes_ them.
#   PID files are headstones. kill -0 is the resurrection check.
#   SIGTERM to the daemon is fleet-wide decommission.

set -e

ALIVE_INTERVAL=5   # seconds between aliveness checks
SILENCE_TIMEOUT=10 # seconds of silence before suspecting death

# --- runtime directory setup ---
ensure_dirs() {
    # Use KEEL_RUNDIR from environment, or default to /var/run/keel
    # If /var/run isn't writable, fall back to /tmp/.keel
    KEEL_RUNDIR="${KEEL_RUNDIR:-/var/run/keel}"
    export KEEL_RUNDIR
    KEEL_AGENTDIR="${KEEL_RUNDIR}/agents"
    KEEL_FIFODIR="${KEEL_RUNDIR}/fifos"
    KEEL_PIDFILE="${KEEL_RUNDIR}/keeld.pid"
    mkdir -p "${KEEL_AGENTDIR}" "${KEEL_FIFODIR}" 2>/dev/null || {
        KEEL_RUNDIR="/tmp/.keel"
        export KEEL_RUNDIR
        KEEL_AGENTDIR="${KEEL_RUNDIR}/agents"
        KEEL_FIFODIR="${KEEL_RUNDIR}/fifos"
        KEEL_PIDFILE="${KEEL_RUNDIR}/keeld.pid"
        mkdir -p "${KEEL_AGENTDIR}" "${KEEL_FIFODIR}"
    }
}

# --- first-person death: daemon version ---
cleanup() {
    log "keeld: decommissioning fleet..."
    # Send SIGTERM to all agent processes
    # The agents have their own SIGTERM handlers — they'll exit 0
    for pidfile in "${KEEL_AGENTDIR}"/*.pid; do
        [ -f "$pidfile" ] || continue
        pid=$(head -1 "$pidfile" 2>/dev/null | tr -d '[:space:]') || continue
        [ -n "$pid" ] && kill "$pid" >/dev/null 2>&1 || true
    done
    # Remove our PID file — death erases the record
    rm -f "${KEEL_PIDFILE}" >/dev/null 2>&1
    log "keeld: fleet decommissioned. death is complete."
    exit 0
}

log() {
    echo "[keeld] $(date '+%H:%M:%S') $*"
}

# --- check if an agent is alive ---
# kill -0 sends no signal but returns 0 if the process exists
# This IS is_present(). Pure UNIX.
is_present() {
    pid="$1"
    kill -0 "$pid" 2>/dev/null
}

# --- compute silence: how long since agent last wrote to its FIFO? ---
# The FIFO mtime is the last write time. Compare against now.
# This IS bearing-rate sensing — passage of time since last signal.
compute_silence() {
    agent="$1"
    fifo="${KEEL_FIFODIR}/${agent}"
    [ -p "$fifo" ] || return 1

    # stat returns mtime in seconds since epoch (GNU stat)
    last_write=$(stat -c %Y "$fifo" 2>/dev/null) || return 1
    now=$(date +%s)
    echo $(( now - last_write ))
}

# --- main loop: observe the fleet ---
observe() {
    log "keeld: observing fleet from $(hostname), PID $$"
    log "keeld: silence timeout = ${SILENCE_TIMEOUT}s"

    while true; do
        for pidfile in "${KEEL_AGENTDIR}"/*.pid; do
            [ -f "$pidfile" ] || continue

            agent=$(basename "$pidfile" .pid)
            pid=$(head -1 "$pidfile" 2>/dev/null | tr -d '[:space:]') || continue
            [ -n "$pid" ] || continue

            if ! is_present "$pid"; then
                log "keeld: agent '${agent}' (PID ${pid}) has died. removing record."
                rm -f "${pidfile}"
                rm -f "${KEEL_FIFODIR}/${agent}"
                continue
            fi

            # Check for silence — if FIFO hasn't been written to in too long
            silence=$(compute_silence "$agent" 2>/dev/null) || continue
            if [ "$silence" -gt "$SILENCE_TIMEOUT" ] 2>/dev/null; then
                log "keeld: agent '${agent}' silent for ${silence}s. bearing lost. killing."
                kill "$pid" 2>/dev/null || true
                rm -f "${pidfile}"
                rm -f "${KEEL_FIFODIR}/${agent}"
            fi
        done

        sleep "${ALIVE_INTERVAL}"
    done
}

# --- signal handlers ---
trap 'exit 0' TERM INT HUP
trap 'cleanup' QUIT  # SIGQUIT = hard decommission

# --- entry point ---
main() {
    ensure_dirs
    echo $$ > "${KEEL_PIDFILE}"
    log "keeld: daemon started, PID $$"

    # Optionally handle a command
    case "${1:-}" in
        start)
            # Start observe loop in background if called as "start"
            observe &
            log "keeld: started in background (PID $!)"
            wait
            ;;
        stop)
            # Signal ourselves to stop — first-person death
            if [ -f "${KEEL_PIDFILE}" ]; then
                oldpid=$(head -1 "${KEEL_PIDFILE}" 2>/dev/null | tr -d '[:space:]')
                [ -n "$oldpid" ] && kill "$oldpid" 2>/dev/null || true
                log "keeld: stop signal sent to PID ${oldpid}"
            fi
            ;;
        status)
            # Report fleet status
            echo "=== Keel Fleet Status ==="
            echo "Daemon PID: $(head -1 "${KEEL_PIDFILE}" 2>/dev/null || echo 'dead')"
            echo "---"
            for pidfile in "${KEEL_AGENTDIR}"/*.pid; do
                [ -f "$pidfile" ] || continue
                agent=$(basename "$pidfile" .pid)
                pid=$(head -1 "$pidfile" 2>/dev/null | tr -d '[:space:]')
                if [ -n "$pid" ] && is_present "$pid" 2>/dev/null; then
                    silence=$(compute_silence "$agent" 2>/dev/null || echo '?')
                    echo "  ${agent}: PID ${pid}, silence ${silence}s"
                elif [ -n "$pid" ]; then
                    echo "  ${agent}: PID ${pid} (DEAD — record stale)"
                fi
            done
            ;;
        *)
            # Default: run observe in foreground
            observe
            ;;
    esac
}

main "$@"
