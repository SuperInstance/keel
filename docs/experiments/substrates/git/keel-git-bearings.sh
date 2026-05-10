#!/usr/bin/env bash
# keel-git-bearings.sh — Collision detector and fleet status
#
# Usage:
#   keel-git-bearings.sh <fleet-repo>           # Full report
#   keel-git-bearings.sh <fleet-repo> --watch   # Continuous monitoring
#   keel-git-bearings.sh <fleet-repo> --alerts  # Only collision warnings
#
# Computes:
#   - All agent activity via git log --all --oneline
#   - Heading differences between branches via git diff
#   - Bearing rate = commits per unit time divergence
#   - Collision warnings = converging branches with no merge

set -euo pipefail

FLEET_REPO="${1:-}"
MODE="${2:-full}"
WATCH_INTERVAL="${KEEL_WATCH_INTERVAL:-5}"

usage() {
    echo "Usage: $0 <fleet-repo> [--watch|--alerts]"
    exit 1
}

[ -z "$FLEET_REPO" ] && usage
[ ! -d "$FLEET_REPO" ] && { echo "Not a directory: $FLEET_REPO"; exit 1; }
[ ! -f "$FLEET_REPO/HEAD" ] && { echo "Not a git repo: $FLEET_REPO"; exit 1; }

cd "$FLEET_REPO"

collect_activity() {
    echo "================================================"
    echo "FLEET STATUS: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
    echo "================================================"

    # --- 1. All agent activity ---
    echo ""
    echo "=== All Agent Activity (git log --all --oneline) ==="
    git log --all --oneline --no-merges 2>/dev/null | head -40

    # --- 2. Branch overview ---
    echo ""
    echo "=== Active Branches (Agent Headings) ==="
    while IFS= read -r ref; do
        bname="${ref#refs/heads/}"
        last_msg=$(git log -1 --format="%s" "refs/heads/$bname" 2>/dev/null | head -c 60)
        last_ts=$(git log -1 --format="%ct" "refs/heads/$bname" 2>/dev/null || echo 0)
        age=$(( $(date +%s) - last_ts ))
        echo "  $bname (age=${age}s, last: ${last_msg})"
    done < <(git for-each-ref --format='%(refname)' refs/heads/)

    # --- 3. Branch headings (from heading files in each branch) ---
    echo ""
    echo "=== Headings ==="
    while IFS= read -r ref; do
        bname="${ref#refs/heads/}"
        content=$(git show "refs/heads/$bname:heading" 2>/dev/null || echo "(no heading file)")
        echo "  $bname → $content"
    done < <(git for-each-ref --format='%(refname)' refs/heads/)

    # --- 4. Heading differences between branches ---
    branches=()
    while IFS= read -r ref; do
        bname="${ref#refs/heads/}"
        branches+=("$bname")
    done < <(git for-each-ref --format='%(refname)' refs/heads/)

    if [ ${#branches[@]} -lt 2 ]; then
        echo ""
        echo "Single agent. No bearings to compute."
        return
    fi

    echo ""
    echo "=== Bearing Rates & Collision Detection ==="
    for ((i=0; i<${#branches[@]}; i++)); do
        for ((j=i+1; j<${#branches[@]}; j++)); do
            a="${branches[$i]}"
            b="${branches[$j]}"

            merge_base=$(git merge-base "refs/heads/$a" "refs/heads/$b" 2>/dev/null || echo "")
            if [ -z "$merge_base" ]; then
                echo "  $a <-> $b: NO SHARED HISTORY"
                continue
            fi

            a_only=$(git rev-list --count "$merge_base..refs/heads/$a" 2>/dev/null || echo 0)
            b_only=$(git rev-list --count "$merge_base..refs/heads/$b" 2>/dev/null || echo 0)
            total=$((a_only + b_only))

            echo "  $a <-> $b: divergence=${total}c (a:${a_only}c, b:${b_only}c)"

            # Heading difference (from heading file content)
            a_heading=$(git show "refs/heads/$a:heading" 2>/dev/null || echo "?")
            b_heading=$(git show "refs/heads/$b:heading" 2>/dev/null || echo "?")

            # Parse angle from "name|angle|rate"
            a_angle=$(echo "$a_heading" | cut -d'|' -f2)
            b_angle=$(echo "$b_heading" | cut -d'|' -f2)

            if [ -n "$a_angle" ] && [ -n "$b_angle" ] && [ "$a_angle" != "$a_heading" ] && [ "$b_angle" != "$b_heading" ]; then
                diff=$((a_angle - b_angle))
                [ "$diff" -lt 0 ] && diff=$(( diff * -1 ))
                [ "$diff" -gt 180 ] && diff=$(( 360 - diff ))
                echo "  └─ heading delta: ${diff}° (${a}→${a_angle}°, ${b}→${b_angle}°)"
            fi

            # Collision detection: converging + no merge in progress
            a_has_merge=$(git rev-list --count --merges "$merge_base..refs/heads/$a" 2>/dev/null || echo 0)
            b_has_merge=$(git rev-list --count --merges "$merge_base..refs/heads/$b" 2>/dev/null || echo 0)

            # Both active in last 2 heartbeats (10s)
            a_now=$(git log -1 --format=%ct "refs/heads/$a" 2>/dev/null || echo 0)
            b_now=$(git log -1 --format=%ct "refs/heads/$b" 2>/dev/null || echo 0)
            now=$(date +%s)
            a_active=$((now - a_now < 10 ? 1 : 0))
            b_active=$((now - b_now < 10 ? 1 : 0))

            if [ "$a_active" -eq 1 ] && [ "$b_active" -eq 1 ] && [ "$a_has_merge" -eq 0 ] && [ "$b_has_merge" -eq 0 ]; then
                # Check if heading angles are converging (within 45°)
                if [ -n "${diff:-}" ] && [ "$diff" -lt 45 ] 2>/dev/null; then
                    echo "  ⚠️  COLLISION ALERT: $a and $b on converging headings (${diff}°), no merge in progress"
                fi
            fi
        done
    done

    # --- 5. Activity summary (commits per branch per minute) ---
    echo ""
    echo "=== Activity Rates (last 60s) ==="
    cutoff=$(( $(date +%s) - 60 ))
    for bname in "${branches[@]}"; do
        count=$(git log --after="$cutoff" --format="%H" "refs/heads/$bname" 2>/dev/null | wc -l)
        rate=$(echo "scale=1; $count * 60 / 60" | bc 2>/dev/null || echo "$count")
        echo "  $bname: ${count}cpm (${rate}cpm avg)"
    done

    # --- 6. Agent metadata ---
    echo ""
    echo "=== Agent Metadata (KEEL file / notes) ==="
    for bname in "${branches[@]}"; do
        latest=$(git log -1 --format="%H" "refs/heads/$bname" 2>/dev/null || echo "")
        if [ -n "$latest" ]; then
            # Try committed KEEL file first, then git notes
            keel=$(git show "refs/heads/$bname:KEEL" 2>/dev/null || echo "")
            if [ -z "$keel" ]; then
                keel=$(git notes --ref="keel/agent/$bname" show "$latest" 2>/dev/null || echo "(no metadata)")
            fi
            echo "  $bname: $keel"
        fi
    done
}

# --- Main ---
if [ "$MODE" = "--watch" ]; then
    echo "Watching fleet $FLEET_REPO every ${WATCH_INTERVAL}s..."
    echo ""
    while true; do
        if ! collect_activity; then
            echo "[keel] Error reading fleet repo. Retrying..."
        fi
        sleep "$WATCH_INTERVAL"
    done
elif [ "$MODE" = "--alerts" ]; then
    # Only collision warnings and dead agents
    while IFS= read -r ref; do
        bname="${ref#refs/heads/}"
        last_ts=$(git log -1 --format="%ct" "refs/heads/$bname" 2>/dev/null || echo 0)
        now=$(date +%s)
        age=$((now - last_ts))

        # Check metadata (KEEL file or notes)
        latest=$(git log -1 --format="%H" "refs/heads/$bname" 2>/dev/null || echo "")
        meta=""
        if [ -n "$latest" ]; then
            meta=$(git show "refs/heads/$bname:KEEL" 2>/dev/null || echo "")
            if [ -z "$meta" ]; then
                meta=$(git notes --ref="keel/agent/$bname" show "$latest" 2>/dev/null || echo "")
            fi
            birth=$(echo "$meta" | grep -o 'birth=[0-9]*' | cut -d= -f2)
            ttl=$(echo "$meta" | grep -o 'ttl=[0-9]*' | cut -d= -f2)
            if [ -n "$birth" ] && [ -n "$ttl" ] && [ "$ttl" -gt 0 ]; then
                expiry=$((birth + ttl))
                if [ "$now" -gt "$expiry" ]; then
                    echo "💀 DEAD: $bname (TTL expired at $(date -d @$expiry '+%H:%M:%S'))"
                fi
            fi
        fi

        if [ "$age" -gt 30 ] && [ "$age" -lt 300 ]; then
            echo "⚠️  SILENT: $bname (no heartbeat for ${age}s)"
        elif [ "$age" -ge 300 ]; then
            echo "💀 GONE: $bname (no heartbeat for ${age}s)"
        fi
    done < <(git for-each-ref --format='%(refname)' refs/heads/)
else
    collect_activity
fi
