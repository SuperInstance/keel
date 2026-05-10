#!/usr/bin/env bash
# keel-git-init.sh — Create a bare fleet repo with Keel hooks
#
# Usage: keel-git-init.sh [path/to/fleet.git]
#
# The bare repo at <path> is THE FIELD. All agents push here.
# Branches are headings. Commits are heartbeats.
# Notes carry birth/ttl metadata. Hooks enforce death-as-default.

set -euo pipefail

FLEET_REPO="${1:-fleet.git}"

echo "=== Keel Git Init ==="
echo "Creating fleet repo at: $FLEET_REPO"

# Create bare repo
git init --bare "$FLEET_REPO"

# Force local hooks path (override any global core.hooksPath setting)
git --git-dir="$FLEET_REPO" config core.hooksPath hooks

cd "$FLEET_REPO"

# ---- refs/notes/commit/ - namespaced notes for agent metadata ----
# git notes use refs/notes/commits by default, but we also allow
# a separate ref under refs/notes/keel for richer metadata.
# We'll use the commit-notes approach: each agent pushes a note
# ref alongside its heartbeats.

# ---- hooks/pre-receive - TTL ENFORCEMENT ----
# Rejects pushes from stale agents (dead by default).
# Agents must have a valid notes/metadata ref or their push is rejected.
cat > hooks/pre-receive << 'PREHOOK'
#!/usr/bin/env bash
# pre-receive — reject pushes from expired agents
#
# Death is default. An agent lives only if its metadata shows a
# birth time and the TTL hasn't expired.
#
# Reads stdin: <old-value> <new-value> <ref-name>
# Exits non-zero to reject the push.

set -euo pipefail

VERBOSE="${KEEL_VERBOSE:-0}"

while read oldrev newrev refname; do
    # Skip tag pushes, note pushes, and internal refs
    case "$refname" in
        refs/notes/*)   continue ;;
        refs/tags/*)    continue ;;
        refs/heads/*)   ;;  # process
        *)              continue ;;
    esac

    branch="${refname#refs/heads/}"

    # Deletion is always allowed (death)
    if [ "$newrev" = "0000000000000000000000000000000000000000" ]; then
        [ "$VERBOSE" -ge 1 ] && echo "[keel] OK: $branch deleted (death-as-default)"
        continue
    fi

    # New branch — allow creation (agent is born)
    if [ "$oldrev" = "0000000000000000000000000000000000000000" ]; then
        [ "$VERBOSE" -ge 1 ] && echo "[keel] OK: $branch born"
        continue
    fi

    # Existing branch — read KEEL metadata file from the previous commit
    # (oldrev is the current tip which has the metadata committed)
    KEEL_CONTENT=$(git show "${oldrev}:KEEL" 2>/dev/null || echo "")

    if [ -z "$KEEL_CONTENT" ]; then
        # No KEEL file — check notes as fallback, then reject
        NOTE_CONTENT=$(git notes --ref="keel/agent/$branch" show "$oldrev" 2>/dev/null || echo "")
        if [ -z "$NOTE_CONTENT" ]; then
            echo "[keel] REJECTED: $branch has no metadata (stale agent)"
            echo "[keel] Death is default. Every branch must carry KEEL metadata:"
            echo "  echo 'birth=<unix_ts>|ttl=<seconds>' > KEEL && git add KEEL && git commit && git push"
            exit 1
        fi
        KEEL_CONTENT="$NOTE_CONTENT"
    fi

    # Parse birth and TTL from metadata
    birth=$(echo "$KEEL_CONTENT" | grep -o 'birth=[0-9]*' | cut -d= -f2)
    ttl=$(echo "$KEEL_CONTENT" | grep -o 'ttl=[0-9]*' | cut -d= -f2)
    now=$(date +%s)

    if [ -z "$birth" ] || [ -z "$ttl" ]; then
        echo "[keel] REJECTED: $branch metadata incomplete (need birth= and ttl=)"
        exit 1
    fi

    expiry=$((birth + ttl))
    if [ "$now" -gt "$expiry" ]; then
        age=$((now - birth))
        echo "[keel] REJECTED: $branch is DEAD (age=${age}s > ttl=${ttl}s)"
        echo "[keel] Death is default. Renew by recommitting the KEEL file."
        exit 1
    fi

    [ "$VERBOSE" -ge 1 ] && echo "[keel] OK: $branch (age=$((now - birth))s, ttl=${ttl}s)"
done

exit 0
PREHOOK
chmod +x hooks/pre-receive

# ---- hooks/post-receive - Bearing Computation ----
# After every push, compute bearing rates between all active branches.
# Bearing rate = divergence in commits-per-unit-time.
cat > hooks/post-receive << 'POSTHOOK'
#!/usr/bin/env bash
# post-receive — compute bearing rates between branches
#
# After each push, logs relative motion of all branches.
# This is the navigation officer's readout.

set -euo pipefail

KEEL_LOGDIR="${KEEL_LOGDIR:-/tmp/keel-logs}"
mkdir -p "$KEEL_LOGDIR"

LOG_FILE="$KEEL_LOGDIR/bearings-$(date +%s).log"

{
    echo "=== Bearings $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

    # List all active branches (not notes/tags)
    branches=()
    while IFS= read -r ref; do
        bname="${ref#refs/heads/}"
        branches+=("$bname")
    done < <(git for-each-ref --format='%(refname)' refs/heads/)

    if [ ${#branches[@]} -lt 2 ]; then
        echo "Single agent active. No bearing computation needed."
        exit 0
    fi

    # For each pair of branches, compute divergence
    for ((i=0; i<${#branches[@]}; i++)); do
        for ((j=i+1; j<${#branches[@]}; j++)); do
            a="${branches[$i]}"
            b="${branches[$j]}"

            # Merge base = point of closest shared ancestry
            merge_base=$(git merge-base "refs/heads/$a" "refs/heads/$b" 2>/dev/null || echo "")
            if [ -z "$merge_base" ]; then
                echo "BEARING: $a <-> $b: NO SHARED HISTORY (different fleet generations?)"
                continue
            fi

            # Divergence = commits unique to each branch since merge base
            a_only=$(git rev-list --count "$merge_base..refs/heads/$a" 2>/dev/null || echo 0)
            b_only=$(git rev-list --count "$merge_base..refs/heads/$b" 2>/dev/null || echo 0)
            total_divergence=$((a_only + b_only))

            # Bearing rate = commits-per-unit-time (approximate)
            # Use timestamps of most recent commits on each branch
            a_time=$(git log -1 --format=%ct "refs/heads/$a" 2>/dev/null || echo 0)
            b_time=$(git log -1 --format=%ct "refs/heads/$b" 2>/dev/null || echo 0)
            now=$(date +%s)
            rate_a=0
            rate_b=0
            [ "$now" -gt "$a_time" ] && rate_a=$(( (a_only * 3600) / (now - a_time + 1) ))  # commits/hour
            [ "$now" -gt "$b_time" ] && rate_b=$(( (b_only * 3600) / (now - b_time + 1) ))

            # Heading difference (branch names as nav vectors for now)
            # In production, headings come from the heading file content
            echo "BEARING: $a (${rate_a}cph) <-> $b (${rate_b}cph) | divergence=${total_divergence}c | base=${merge_base:0:8}"

            # Collision warning: converging heads with no merge in progress
            a_has_merge=$(git rev-list --count --merges "$merge_base..refs/heads/$a" 2>/dev/null || echo 0)
            b_has_merge=$(git rev-list --count --merges "$merge_base..refs/heads/$b" 2>/dev/null || echo 0)
            if [ "$a_has_merge" -eq 0 ] && [ "$b_has_merge" -eq 0 ]; then
                # Check if both are making commits (converging)
                if [ "$rate_a" -gt 0 ] && [ "$rate_b" -gt 0 ]; then
                    echo "⚠️  COLLISION WARNING: $a and $b converging, no merge in progress"
                fi
            fi
        done
    done

    echo "=== End bearings ==="
} >> "$LOG_FILE" 2>&1

# Keep only last 100 log entries
ls -t "$KEEL_LOGDIR"/bearings-*.log 2>/dev/null | tail -n +101 | xargs -r rm -f

echo "[keel] Bearings logged to $LOG_FILE"
POSTHOOK
chmod +x hooks/post-receive

# ---- hooks/update - Gatekeeping Individual Ref Updates ----
cat > hooks/update << 'UPDATEHOOK'
#!/usr/bin/env bash
# update — lightweight per-ref TTL check (faster for individual checks)
# Delegates to the same logic as pre-receive for consistency.

set -euo pipefail

refname="$1"
oldrev="$2"
newrev="$3"

# Reuse the pre-receive logic via stdin injection
echo "$oldrev $newrev $refname" | bash hooks/pre-receive
UPDATEHOOK
chmod +x hooks/update

# ---- Summary ----
echo ""
echo "=== Fleet repo ready at $FLEET_REPO ==="
echo ""
echo "Structure:"
echo "  refs/heads/<agent>    — Agent headings (branches)"
echo "  refs/notes/keel/agent/<agent>  — Agent metadata (birth, TTL)"
echo ""
echo "Hooks installed:"
echo "  pre-receive  — Rejects stale/expired agent pushes"
echo "  post-receive — Logs bearing rates between branches"
echo "  update       — Per-ref TTL enforcement"
echo ""
echo "Agents can now push:"
echo "  git clone $FLEET_REPO agent-workspace"
echo "  # or work directly from a clone"
echo ""
echo "Death is default. Silence IS death."
