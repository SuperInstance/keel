#!/usr/bin/env bash
# keel-git-agent.sh — Agent process that lives through git heartbeats
#
# Usage: keel-git-agent.sh <agent-name> <fleet-repo> [options]
#
# An agent:
#   1. Clones or pulls the fleet repo
#   2. Creates a branch named after itself
#   3. Ships a heading: echo "heading|angle|rate" > heading && git commit
#   4. Pushes every heartbeat (git push IS the heartbeat)
#   5. Writes git notes for birth/ttl metadata
#   6. Dies when it stops pushing (death is default)

set -euo pipefail

AGENT_NAME="${1:-}"
FLEET_REPO="${2:-}"
WORK_DIR="/tmp/keel-agents/$AGENT_NAME"
HEARTBEAT="${KEEL_HEARTBEAT:-5}"          # seconds between heartbeats
TTL="${KEEL_TTL:-60}"                     # total lifespan in seconds (0 = immortal)
HEADING_CHANGE="${KEEL_HEADING_CHANGE:-0.1}"  # probability of changing heading each beat

usage() {
    echo "Usage: $0 <agent-name> <fleet-repo>"
    echo ""
    echo "Environment variables:"
    echo "  KEEL_HEARTBEAT       Seconds between heartbeats (default: 5)"
    echo "  KEEL_TTL             Total lifespan in seconds (default: 60, 0=immortal)"
    echo "  KEEL_HEADING_CHANGE  Probability of changing heading per beat (default: 0.1)"
    echo "  KEEL_VERBOSE         Set to 1 for verbose output"
    exit 1
}

[ -z "$AGENT_NAME" ] && usage
[ -z "$FLEET_REPO" ] && usage

# --- Init ---
BIRTH=$(date +%s)
DEATH_AT=$((BIRTH + TTL))
[ "$TTL" -eq 0 ] && DEATH_AT=0  # immortal

mkdir -p "$WORK_DIR"

# Clone or pull
if [ -d "$WORK_DIR/.git" ]; then
    cd "$WORK_DIR"
    git pull --rebase origin "$AGENT_NAME" 2>/dev/null || true
else
    git clone "$FLEET_REPO" "$WORK_DIR"
    cd "$WORK_DIR"
fi

# Create branch (from orphan if first time)
if ! git show-ref --verify "refs/heads/$AGENT_NAME" 2>/dev/null; then
    git checkout --orphan "$AGENT_NAME"
    rm -f heading heading.* KEEL 2>/dev/null || true
    echo "birth=${BIRTH}|ttl=${TTL}|agent=${AGENT_NAME}" > KEEL
    git add KEEL
    git commit -m "keel: birth of agent $AGENT_NAME at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
else
    git checkout "$AGENT_NAME"
fi

# --- Main loop ---
BEAT=0

echo "[keel] Agent $AGENT_NAME born at $(date -u -d @$BIRTH '+%Y-%m-%dT%H:%M:%SZ')"
[ "$DEATH_AT" -gt 0 ] && echo "[keel] TTL: ${TTL}s, expires at $(date -u -d @$DEATH_AT '+%Y-%m-%dT%H:%M:%SZ')"
echo "[keel] Heartbeat: ${HEARTBEAT}s | Heading change: ${HEADING_CHANGE}"
echo ""

while true; do
    # Check death
    NOW=$(date +%s)
    if [ "$DEATH_AT" -gt 0 ] && [ "$NOW" -gt "$DEATH_AT" ]; then
        echo "[keel] TTL expired. $AGENT_NAME dies. Silence IS death."
        exit 0
    fi

    BEAT=$((BEAT + 1))

    # Pick heading (with random change)
    HEADING_FILE="$WORK_DIR/heading"
    if [ ! -f "$HEADING_FILE" ] || awk "BEGIN {srand(); exit(rand() < $HEADING_CHANGE ? 0 : 1)}"; then
        # New random heading: name | degrees (0-359) | rate (speed)
        hdg_name="hdg-$(head /dev/urandom | md5sum | head -c 8)"
        hdg_angle=$((RANDOM % 360))
        hdg_rate=$((RANDOM % 10 + 1))
        echo "${hdg_name}|${hdg_angle}|${hdg_rate}" > "$HEADING_FILE"
    fi
    HEADING=$(cat "$HEADING_FILE")

    # Update KEEL metadata (always committed so pre-receive can read it)
    echo "birth=${BIRTH}|ttl=${TTL}|agent=${AGENT_NAME}|beat=${BEAT}|heading=${HEADING}|ts=$(date +%s)" > KEEL

    # Commit
    git add heading KEEL
    git commit --allow-empty -m "beat $BEAT | $HEADING | ts=$(date +%s)"

    # Push = heartbeat
    git push origin "HEAD:$AGENT_NAME" 2>&1 || {
        echo "[keel] PUSH FAILED — agent $AGENT_NAME cannot reach fleet. Dying."
        exit 1
    }

    echo "[keel] beat $BEAT | $HEADING | ok"

    # Wait for next heartbeat
    sleep "$HEARTBEAT"
done
