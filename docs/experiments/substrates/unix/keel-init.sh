#!/bin/sh
# keel-init.sh — Lay a Keel
#
# Lays a keel by creating a PID file with a timestamp.
# The keel date is the birth certificate of a managed process.
# Every process in the fleet is laid on a keel.
#
# Philosophy:
#   A keel is NOT a config file. A keel is a birth record.
#   The PID file is the keel. The timestamp is the launch time.
#   No keel = no ship. No PID = no agent.
#   The keel is always laid BEFORE the agent is launched.
#
# Usage:
#   ./keel-init.sh <agent-name> [command...]
#
# Examples:
#   ./keel-init.sh scout-1 /usr/bin/sensor-read
#   ./keel-init.sh relay-a socat TCP-LISTEN:8080 -
#   ./keel-init.sh my-agent ./keel-agent.sh --heading "270" --ttl 30

set -e

KEEL_RUNDIR="${KEEL_RUNDIR:-/var/run/keel}"
KEEL_AGENTDIR="${KEEL_RUNDIR}/agents"
KEEL_FIFODIR="${KEEL_RUNDIR}/fifos"
KEEL_PIDFILE="${KEEL_AGENTDIR}/${1}.pid"  # This IS the keel
KEEL_FIFO="${KEEL_FIFODIR}/${1}"           # This IS the field channel

# --- first-person death for init itself ---
trap 'exit 1' INT TERM HUP

usage() {
    echo "Usage: $0 <agent-name> [command...]" >&2
    echo "  Lays a keel for agent-name, then exec's command" >&2
    echo "  If no command, reads from stdin" >&2
    exit 1
}

main() {
    [ -n "$1" ] || usage
    agent_name="$1"
    shift

    # --- Ensure directories exist (the daemon should have created these) ---
    mkdir -p "${KEEL_AGENTDIR}" "${KEEL_FIFODIR}" 2>/dev/null || true

    # --- LAY THE KEEL: write PID + timestamp ---
    # The PID file IS the keel. It contains two values:
    #   line 1: PID (the process identifier — the vessel)
    #   line 2: timestamp (the launch time — the birth)
    # This is the birth certificate. Everything starts here.
    {
        echo "$$"
        date +%s
        echo "Laid: $(date)"
    } > "${KEEL_PIDFILE}"

    # --- CREATE THE FIELD CHANNEL: the named pipe ---
    # The FIFO is the agent's communication channel.
    # Other agents can read from it to get this agent's heading.
    # If the FIFO goes silent, the agent is dead.
    # mkfifo is the field channel — it's the medium, not a message.
    # Suppress all errors — cleanup races are expected.
    mkfifo "${KEEL_FIFO}" >/dev/null 2>&1 || {
        rm -f "${KEEL_FIFO}" >/dev/null 2>&1
        mkfifo "${KEEL_FIFO}" >/dev/null 2>&1 || true
    }

    # --- OPEN THE FIFO FOR WRITING in background ---
    # The FIFO needs both ends open. We keep a writer open.
    # This background subshell keeps the write end alive while the agent runs.
    exec 3>"${KEEL_FIFO}"

    # --- DELETE THE PID FILE ON EXIT — death erases the record ---
    cleanup() {
        # Best-effort cleanup. Silence IS death — closing the FIFO
        # tells readers the agent is gone. All errors suppressed.
        rm -f "${KEEL_PIDFILE}" "${KEEL_FIFO}" >/dev/null 2>&1 || true
        exec 3>&- 2>/dev/null || true
    }
    trap 'cleanup; exit 0' TERM INT HUP QUIT EXIT

    # --- EXEC THE COMMAND (or read from stdin) ---
    # exec replaces this process with the agent.
    # The keel (PID file) still points at this PID because exec inherits it.
    # The keel survives the exec — the vessel IS the process, not the shell.
    if [ $# -ge 1 ]; then
        # Execute the command with its arguments
        # The command inherits file descriptor 3 for the FIFO
        exec "$@"
    else
        # Read from stdin and pipe to the FIFO
        # This turns stdin into agent heading data
        while IFS= read -r line; do
            echo "$line" >&3
        done
    fi
}

main "$@"
