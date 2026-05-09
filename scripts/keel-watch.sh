#!/usr/bin/env bash
# keel-watch.sh — Night watch heartbeat daemon
# Keeps the boat afloat while Casey sleeps.
# Runs keel heartbeat every 5 minutes.

INTERVAL=300  # 5 minutes
LOG=/tmp/keel-watch.log
PIDFILE=/tmp/keel-watch.pid

echo "🔮 Keel Watch starting — $(date)" | tee -a "$LOG"
echo "   Interval: ${INTERVAL}s" | tee -a "$LOG"
echo "   Log: $LOG" | tee -a "$LOG"
echo "   PID: $$" | tee -a "$LOG"
echo "$$" > "$PIDFILE"

# Find the most recent keel workspace
WORKSPACE=$(find /tmp -maxdepth 2 -name ".keel" -type d 2>/dev/null | head -1)
if [ -z "$WORKSPACE" ]; then
    echo "   No keel workspace found. Creating one..."
    cd /tmp && keel init night-watch >/dev/null 2>&1
    WORKSPACE="/tmp/night-watch"
fi

cd "$WORKSPACE"

while true; do
    HEARTBEAT=$(keel heartbeat 2>&1)
    echo "[$(date +%H:%M:%S)] $HEARTBEAT" >> "$LOG"
    sleep "$INTERVAL"
done
