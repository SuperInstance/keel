#!/bin/sh
# keel-agent.sh — A Keel Agent
#
# An agent process in the Keel architecture.
# Every agent carries its own death. No external scheduler kills it.
# The agent knows its TTL. It writes its heading to a named pipe.
# When TTL expires, SIGALRM fires, and the agent dies (exit 0).
#
# Philosophy:
#   trap 'exit 0' SIGALRM — first-person TTL declaration
#   Writing to the FIFO IS the heartbeat. Output = alive. Silence = death.
#   Parent reads the pipe. If empty for N seconds, the agent is assumed dead.
#   The heading IS the agent's state. There is no other state.
#
# Signature of a live agent:
#   kill -0 $pid  →  returns 0
#   cat $fifo    →  yields data (non-blocking)
#
# Signature of a dead agent:
#   kill -0 $pid  →  returns 1
#   cat $fifo    →  hangs forever (no writer)
#
# Usage:
#   ./keel-agent.sh --name scout-1 --heading "270@12kt" --ttl 30
#   ./keel-agent.sh --name logger-1 --heading "standby" --ttl 60
#
# Options:
#   --name <name>     Agent identifier (default: agent-$$)
#   --heading <str>   The heading/status to broadcast (default: "alive")
#   --ttl <seconds>   Time to live before self-termination (default: 30)
#   --interval <sec>  How often to write heading (default: 2)

set -e

# --- defaults ---
AGENT_NAME="agent-$$"
HEADING="alive"
TTL=30
INTERVAL=2

KEEL_RUNDIR="${KEEL_RUNDIR:-/var/run/keel}"
KEEL_AGENTDIR="${KEEL_RUNDIR}/agents"
KEEL_FIFODIR="${KEEL_RUNDIR}/fifos"

# --- parse arguments ---
while [ $# -gt 0 ]; do
    case "$1" in
        --name) AGENT_NAME="$2"; shift 2 ;;
        --heading) HEADING="$2"; shift 2 ;;
        --ttl) TTL="$2"; shift 2 ;;
        --interval) INTERVAL="$2"; shift 2 ;;
        *) echo "keel-agent: unknown option $1" >&2; exit 1 ;;
    esac
done

# --- FIRST-PERSON DEATH: I carry my own termination ---
# When SIGALRM fires, I exit 0. Completed successfully then died.
# This is the entire philosophy of the Keel system in one line:
#   Every process carries its own death. No central scheduler.
trap 'echo "[keel-agent:${AGENT_NAME}] TTL expired. Self-terminating."; exit 0' ALRM TERM

# --- FIRST-PERSON DEATH TIMER — I WILL die in TTL seconds ---
# The alarm clock IS the TTL engine. A background sleep triggers SIGALRM.
# The kernel manages this timer. No external process needs to track it.
# `sleep $TTL && kill -ALRM $$ &` = I carry my own death sentence.
(sleep "${TTL}" && kill -ALRM "$$" 2>/dev/null) &
TTL_PID=$!

# --- Set up the FIFO for this agent ---
# The keel-init.sh would normally create this, but we can also self-create
FIFO="${KEEL_FIFODIR}/${AGENT_NAME}"
PIDFILE="${KEEL_AGENTDIR}/${AGENT_NAME}.pid"

mkdir -p "${KEEL_AGENTDIR}" "${KEEL_FIFODIR}" 2>/dev/null || true

# Write our PID as the keel — death erases it
echo "$$" > "${PIDFILE}"
echo "$(date +%s)" >> "${PIDFILE}"

# Create and open FIFO (suppress errors — races with daemon cleanup)
rm -f "${FIFO}" >/dev/null 2>&1 || true
mkfifo "${FIFO}" >/dev/null 2>&1 || true

# Open the FIFO for writing on fd 3
exec 3>"${FIFO}" 2>/dev/null || true

# --- Cleanup on death ---
cleanup() {
    rm -f "${PIDFILE}" >/dev/null 2>&1 || true
    exec 3>&- >/dev/null 2>&1 || true
    rm -f "${FIFO}" >/dev/null 2>&1 || true
    kill "${TTL_PID}" >/dev/null 2>&1 || true
}
trap 'cleanup' EXIT INT HUP

# --- AGENT LOOP: broadcast heading until death ---
# The loop IS the agent's lifecycle.
# Each iteration writes heading to the FIFO (output IS heartbeat).
# Between writes the agent may do actual work (computation, sensing, etc.)
# When SIGALRM fires, the loop is interrupted and exit 0 runs.

echo "[keel-agent:${AGENT_NAME}] launched. heading=${HEADING}, ttl=${TTL}s, pid=$$"

ITERATION=0
while true; do
    # Output IS heartbeat — writing to stdout (and to FIFO) IS aliveness
    # The parent process reads from the FIFO.
    # If the FIFO goes silent for N seconds, the parent knows we're dead.
    timestamp=$(date -Iseconds 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S%z")
    echo "${timestamp} ${AGENT_NAME} ${HEADING} iter=${ITERATION}" >&3

    # Also write to stdout for direct observation
    echo "${timestamp} ${AGENT_NAME} ${HEADING} iter=${ITERATION}"

    ITERATION=$((ITERATION + 1))
    sleep "${INTERVAL}"
done
