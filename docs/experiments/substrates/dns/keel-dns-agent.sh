#!/bin/bash
# keel-dns-agent.sh — Keel TTL Engine Agent
#
# An agent that lives in DNS. Every heartbeat = zone record update.
# Stop updating = TTL expires = NXDOMAIN = you are dead.
# dig IS the bearing-rate sensor.
#
# Usage:
#   ./keel-dns-agent.sh <agent-name> [zone-file] [server-port]
#
# Example:
#   ./keel-dns-agent.sh agent-01 /tmp/keel.db 5353
#
# Architecture:
#   The agent maintains its own records in a DNS zone file.
#   A companion server (keel-dns-server.py) serves that zone.
#   The agent does NOT tell the server "I'm alive" — it updates a RECORD.
#   The record carries its own TTL. When the update stops, TTL expires.
#   This is first-person death: the record decides when to die.
#
# TTL Constants:
#   AGENT_TTL=60    — Agent presence heartbeat (A record)
#   HEADING_TTL=15  — Heading changes rapidly
#   BEARING_TTL=30  — Bearing observations
#
# dig as Sensor:
#   The agent queries other agents' A records. If NXDOMAIN, they're dead.
#   The agent queries bearing records to sense fleet movement.
#   dig is the sensor. The response is the measurement.

set -euo pipefail

# ─── Configuration ───────────────────────────────────────────────────────

AGENT_NAME="${1:-agent-01}"
ZONE_FILE="${2:-/tmp/keel.db}"
SERVER_PORT="${3:-5353}"
SERVER_HOST="127.0.0.1"
ZONE="fleet.example"
AGENT_IP="${AGENT_IP:-10.0.0.$((RANDOM % 250 + 1))}"

# TTL constants (the death timers)
AGENT_TTL=60      # Agent presence: check-in every 60s or die
HEADING_TTL=15    # Heading: fast-changing, short cache
BEARING_TTL=30    # Bearing: moderate staleness
TRUST_TTL=3600    # Trust: slow-moving, cache for an hour

# Agent identity (born once, immutable)
BIRTH_TS=$(date +%s)

# State
HEARTBEAT=0
FLEET=("agent-01" "agent-02" "agent-03")  # Known fleet members to sense

# ─── Colors ──────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ─── Helpers ─────────────────────────────────────────────────────────────

msg()  { echo -e "${BLUE}[${AGENT_NAME}]${NC} $*"; }
alive(){ echo -e "${GREEN}[${AGENT_NAME}]${NC} $*"; }
dead() { echo -e "${RED}[${AGENT_NAME} ✗]${NC} $*"; }
warn() { echo -e "${YELLOW}[${AGENT_NAME}]${NC} $*"; }

update_zone_record() {
    local name="$1" type="$2" ttl="$3" data="$4"
    local fullname="${name}.${ZONE}"

    # Remove old record if exists
    if grep -q "^${name}[[:space:]].*${type}" "$ZONE_FILE" 2>/dev/null; then
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "/^${name}[[:space:]].*${type}/d" "$ZONE_FILE"
        else
            sed -i "/^${name}[[:space:]].*${type}/d" "$ZONE_FILE"
        fi
    fi

    # Add new record (insert after $TTL line or before SOA)
    # Find the right insertion point
    local insert_after
    case "$type" in
        A)   insert_after="SOA" ;;   # A records after SOA
        TXT) insert_after="SOA" ;;   # TXT near A records
        *)   insert_after="SOA" ;;
    esac

    # Simple: just append
    echo "${name} ${ttl} IN ${type} \"${data}\"" >> "$ZONE_FILE"
}

remove_agent_records() {
    # Called on death — remove all records for this agent
    if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' "/^${AGENT_NAME}[[:space:]]/d" "$ZONE_FILE"
    else
        sed -i "/^${AGENT_NAME}[[:space:]]/d" "$ZONE_FILE"
    fi
    alive "Records removed. Agent deleted from zone."
}

publish_presence() {
    # Write A record = "I am alive at this IP for TTL seconds"
    local now=$(date +%s)
    update_zone_record "$AGENT_NAME" "A" "$AGENT_TTL" "$AGENT_IP"
    alive "Published presence at ${AGENT_IP}  [TTL=${AGENT_TTL}s]"
}

publish_heading() {
    # Write heading TXT record = "I am moving in this direction"
    local direction=$((RANDOM % 360))
    local rate=$(awk -v seed=$RANDOM 'BEGIN{srand(seed); printf "%.2f", rand()}')
    local now=$(date +%s)
    local heading_data="heading|${direction}|${rate}|birth=${BIRTH_TS}"
    update_zone_record "$AGENT_NAME" "TXT" "$HEADING_TTL" "$heading_data"
    alive "Published heading ${direction}° at ${rate}/s  [TTL=${HEADING_TTL}s]"
}

sense_bearing() {
    # Use dig to sense another agent — dig IS the bearing-rate sensor
    local target="$1"
    local fullname="${target}.${ZONE}"
    local sensor_name="bearing.${AGENT_NAME}.${target}"

    # Query target's A record
    local result
    result=$(dig @${SERVER_HOST} -p ${SERVER_PORT} "${fullname}" A +short 2>/dev/null || true)

    if [[ -z "$result" || "$result" == *"NXDOMAIN"* || "$result" == *"SERVFAIL"* ]]; then
        dead "${target}: NXDOMAIN (agent is dead)"
        # Optionally publish bearing with death observation
        local now=$(date +%s)
        # Remove bearing record — target is dead, no bearing needed
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "/^${sensor_name}[[:space:]]/d" "$ZONE_FILE" 2>/dev/null || true
        else
            sed -i "/^${sensor_name}[[:space:]]/d" "$ZONE_FILE" 2>/dev/null || true
        fi
        return 1
    fi

    # Calculate bearing (simulated from positions)
    local target_ip=$(echo "$result" | head -1)
    local target_last_octet=$(echo "$target_ip" | awk -F'.' '{print $4}')
    local my_last_octet=$(echo "$AGENT_IP" | awk -F'.' '{print $4}')
    local angle=$(( (target_last_octet - my_last_octet + 360) % 360 ))
    local rate=$(awk -v a=$angle -v s=$RANDOM 'BEGIN{srand(s); printf "%.2f", (rand()-0.5)*0.8}')
    local now=$(date +%s)
    local bearing_data="bearing|${angle}|${rate}|observed=${now}"

    update_zone_record "$sensor_name" "TXT" "$BEARING_TTL" "$bearing_data"
    msg "Sensed ${target} → ${target_ip}  bearing ${angle}° rate ${rate}  [TTL=${BEARING_TTL}s]"
}

publish_trust() {
    # Trust assertion — slowly changing; written once, refreshed rarely
    local target="${1:-$AGENT_NAME}"
    local trust_name="trust.${target}"
    local confidence=$(awk -v s=$RANDOM 'BEGIN{srand(s); printf "%.2f", 0.5 + rand()*0.5}')
    local depth=0
    [[ "$target" != "$AGENT_NAME" ]] && depth=1
    local now=$(date +%s)
    local trust_data="trust|${confidence}|${depth}|proven=${now}"

    update_zone_record "$trust_name" "TXT" "$TRUST_TTL" "$trust_data"
    msg "Trust on ${target}: ${confidence} (depth=${depth})  [TTL=${TRUST_TTL}s]"
}

fleet_scan() {
    # Scan all known fleet members
    msg "--- Fleet Scan ---"
    for member in "${FLEET[@]}"; do
        [[ "$member" == "$AGENT_NAME" ]] && continue
        sense_bearing "$member" || true
    done
    msg "--- Scan Complete ---"
}

clean_zone_header() {
    # Ensure zone file has proper header
    if [[ ! -f "$ZONE_FILE" ]]; then
        {
            echo "\$ORIGIN ${ZONE}."
            echo "\$TTL ${AGENT_TTL}"
            echo ""
        } > "$ZONE_FILE"
    fi

    # Add header if missing
    if ! grep -q "^\$ORIGIN" "$ZONE_FILE" 2>/dev/null; then
        local tmpfile=$(mktemp)
        {
            echo "\$ORIGIN ${ZONE}."
            echo "\$TTL ${AGENT_TTL}"
            echo ""
            cat "$ZONE_FILE"
        } > "$tmpfile"
        mv "$tmpfile" "$ZONE_FILE"
    fi
}

die() {
    # Graceful death: remove records from zone
    # TTL will expire naturally, but let's be clean about it
    warn "Agent ${AGENT_NAME} shutting down..."
    remove_agent_records
    alive "Records removed. TTL will expire. ${AGENT_NAME} will be NXDOMAIN."
    alive "Goodbye."
    exit 0
}

# ─── Main Loop ───────────────────────────────────────────────────────────

main() {
    alive "Agent ${AGENT_NAME} booting at ${AGENT_IP} (birth: ${BIRTH_TS})"
    alive "Serving from: ${ZONE_FILE} @ ${SERVER_HOST}:${SERVER_PORT}"
    alive "TTL Constants: PRESENCE=${AGENT_TTL}s HEADING=${HEADING_TTL}s BEARING=${BEARING_TTL}s TRUST=${TRUST_TTL}s"
    echo ""

    # Trap for graceful shutdown
    trap die SIGINT SIGTERM

    clean_zone_header

    HEARTBEAT=0
    while true; do
        HEARTBEAT=$((HEARTBEAT + 1))
        echo ""
        msg "── Heartbeat #${HEARTBEAT} ──────────────────────────────"

        # Publish presence (A record — the death timer)
        publish_presence

        # Publish heading (TXT record — current trajectory)
        publish_heading

        # Fleet scan — sense bearings to other agents
        fleet_scan

        # Publish trust (every 10th heartbeat)
        if (( HEARTBEAT % 10 == 0 )); then
            publish_trust "$AGENT_NAME"
            for member in "${FLEET[@]}"; do
                [[ "$member" == "$AGENT_NAME" ]] && continue
                publish_trust "$member"
            done
        fi

        msg "Heartbeat #${HEARTBEAT} complete. Next in ${AGENT_TTL}s..."
        echo ""

        # Sleep for heartbeat interval
        # If we stop (process killed, agent crashes), we stop updating
        # The TTL on our records will expire, and we become NXDOMAIN
        sleep "$AGENT_TTL"
    done
}

# ─── Entry Point ─────────────────────────────────────────────────────────

main "$@"
