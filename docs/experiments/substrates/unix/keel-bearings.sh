#!/bin/sh
# keel-bearings.sh — Compute Bearings from Agent Headings
#
# Reads headings from FIFOs, computes relative bearings.
# Bearing = the angular relationship between two agents.
# In navigation, bearing tells you where something is relative to your heading.
# In the Keel architecture, bearings IS the awareness network.
#
# Philosophy:
#   A bearing is NOT a stored relationship. It's computed fresh each time.
#   Reading from a FIFO IS sensing. If the FIFO is empty, the agent is silent.
#   Silence does NOT mean death — it means NO SIGNAL RECEIVED.
#   That's a crucial distinction. An agent might be alive but bearing-blocked.
#
# Usage:
#   ./keel-bearings.sh                          # show bearings for all agents
#   ./keel-bearings.sh --from scout-1            # bearings from scout-1
#   ./keel-bearings.sh --from scout-1 --to relay-a  # specific pair
#   ./keel-bearings.sh --watch                  # continuous bearing display
#   ./keel-bearings.sh --plot                   # grid-based bearing map

set -e

KEEL_RUNDIR="${KEEL_RUNDIR:-/var/run/keel}"
KEEL_AGENTDIR="${KEEL_RUNDIR}/agents"
KEEL_FIFODIR="${KEEL_RUNDIR}/fifos"

# --- defaults ---
FROM_AGENT=""
TO_AGENT=""
WATCH_MODE=0
PLOT_MODE=0
REFRESH_INTERVAL=2

# --- parse arguments ---
while [ $# -gt 0 ]; do
    case "$1" in
        --from) FROM_AGENT="$2"; shift 2 ;;
        --to) TO_AGENT="$2"; shift 2 ;;
        --watch|-w) WATCH_MODE=1; shift ;;
        --plot|-p) PLOT_MODE=1; shift ;;
        --interval) REFRESH_INTERVAL="$2"; shift 2 ;;
        *) echo "keel-bearings: unknown option $1" >&2; exit 1 ;;
    esac
done

# --- read heading from an agent's FIFO (non-blocking) ---
# Returns the last heading written to the FIFO.
# Uses dd with timeout to avoid hanging on empty FIFO.
read_heading() {
    agent="$1"
    fifo="${KEEL_FIFODIR}/${agent}"

    [ -p "$fifo" ] || {
        echo "${agent}: NO FIFO"
        return 1
    }

    # Try to read from FIFO with timeout (GNU timeout or custom)
    # We read all available data and take the last line
    heading=$(timeout 0.5 cat "$fifo" 2>/dev/null | tail -1) || {
        echo "${agent}: SILENT (no data in ${REFRESH_INTERVAL}s)"
        return 1
    }

    echo "${agent}: ${heading}"
}

# --- parse heading into bearing components ---
# Expected format from keel-agent: "2025-03-15T10:30:00 scout-1 270@12kt iter=42"
# Extracts the heading field (positional: time, name, heading, iter)
parse_bearing() {
    line="$1"
    # Extract heading field (3rd space-separated field)
    heading=$(echo "$line" | awk '{print $3}' 2>/dev/null) || echo "?"
    echo "$heading"
}

# --- list all active agents ---
list_agents() {
    for pidfile in "${KEEL_AGENTDIR}"/*.pid; do
        [ -f "$pidfile" ] || continue
        agent=$(basename "$pidfile" .pid)
        pid=$(cat "$pidfile" 2>/dev/null) || continue
        if kill -0 "$pid" 2>/dev/null; then
            echo "$agent"
        fi
    done
}

# --- compute relative bearing between two agent headings ---
# In real navigation, bearing = direction from observer to target.
# Here, we extract numeric headings and compute the difference.
# If headings contain direction-speed like "270@12kt", extract the direction.
relative_bearing() {
    from_heading="$1"
    to_heading="$2"

    # Extract just the direction (numeric portion before @ if present)
    from_dir=$(echo "$from_heading" | sed 's/@.*//' | grep -o '^[0-9]*' | head -1)
    to_dir=$(echo "$to_heading" | sed 's/@.*//' | grep -o '^[0-9]*' | head -1)

    [ -n "$from_dir" ] && [ -n "$to_dir" ] || {
        echo "???"
        return
    }

    # Compute relative bearing: target bearing - observer bearing
    # In awk to handle floating point
    echo "" | awk -v f="$from_dir" -v t="$to_dir" '{
        rel = t - f;
        if (rel < 0) rel += 360;
        printf "%03.0f", rel
    }'
}

# --- single bearing snapshot ---
snapshot() {
    _from="${FROM_AGENT:-$(list_agents | head -1)}"
    [ -n "$_from" ] || {
        echo "No agents found in ${KEEL_AGENTDIR}"
        exit 1
    }

    from_heading=$(read_heading "$_from" 2>/dev/null) || true

    echo "=== Bearing Snapshot ==="
    echo "Observer: ${from_heading}"
    echo "---"

    for agent in $(list_agents); do
        [ "$agent" = "$_from" ] && continue
        [ -n "$TO_AGENT" ] && [ "$agent" != "$TO_AGENT" ] && continue

        agent_heading=$(read_heading "$agent" 2>/dev/null) || continue

        from_bearing=$(parse_bearing "$from_heading" 2>/dev/null || echo "?")
        to_bearing=$(parse_bearing "$agent_heading" 2>/dev/null || echo "?")

        rel=$(relative_bearing "$from_bearing" "$to_bearing")

        echo "  ${agent}"
        echo "    Heading: ${to_bearing}"
        echo "    Relative Bearing: ${rel}°"
    done
}

# --- bearing map (grid) ---
# Plots agents on a grid based on their headings.
# The bearing map IS the field visualization.
plot_map() {
    echo "=== Keel Bearing Map ==="
    echo ""

    x_max=60
    y_max=20

    # Allocate grid
    grid=""
    y=0; while [ "$y" -le "$y_max" ]; do
        x=0; while [ "$x" -le "$x_max" ]; do
            grid="${grid}."
            x=$((x + 1))
        done
        grid="${grid}\n"
        y=$((y + 1))
    done

    # Place agents on grid based on heading direction and iteration
    for agent in $(list_agents); do
        heading_line=$(read_heading "$agent" 2>/dev/null) || continue
        heading=$(parse_bearing "$heading_line" 2>/dev/null || echo "?")
        iteration=$(echo "$heading_line" | grep -o 'iter=[0-9]*' | grep -o '[0-9]*')

        # Use heading as x-position and iteration as y-position (wrapped)
        px=$(echo "$heading" | sed 's/@.*//' | grep -o '^[0-9]*' | head -1)
        [ -z "$px" ] && px=30
        px=$((px * x_max / 360))
        [ "$px" -gt "$x_max" ] && px=$x_max

        py=$(( (iteration % (y_max + 1)) ))
        [ "$py" -gt "$y_max" ] && py=$y_max

        # Place agent marker
        pos=$(( py * (x_max + 2) + px ))
        agent_char=$(echo "$agent" | cut -c1)
        grid=$(echo "$grid" | sed "s/./${agent_char}/${pos}" )
    done

    echo -e "$grid"
    echo ""
    echo "Legend: each character is an agent's first letter."
    echo "X-axis: heading (0-360°). Y-axis: iteration."
}

# --- continuous watch mode ---
watch_bearings() {
    while true; do
        clear 2>/dev/null || true
        if [ "$PLOT_MODE" -eq 1 ]; then
            plot_map
        else
            snapshot
        fi
        echo ""
        echo "--- refreshing every ${REFRESH_INTERVAL}s (Ctrl+C to stop) ---"
        sleep "${REFRESH_INTERVAL}"
    done
}

# --- signal handling ---
trap 'exit 0' INT TERM HUP

# --- entry point ---
if [ "$WATCH_MODE" -eq 1 ] || [ "$PLOT_MODE" -eq 1 ]; then
    watch_bearings
else
    snapshot
fi
