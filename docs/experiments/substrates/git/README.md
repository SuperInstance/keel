# Keel TTL Engine — Git-Native Fleet

```
git init    = keel init
git push    = heartbeat
git log     = build record
git merge   = collision resolution
git branch -D = death-as-default
```

Git already IS Keel. Branches carry their own history (first-person time).
`git merge` is bearing negotiation. `git rebase` is heading change.
`git branch -D` is death. The entire architecture was hiding in version control.

---

## Why Git Is the Perfect Field

### Distributed, No Central Scheduler
Every agent has a full clone. There is no "orchestrator" or "scheduler" process.
The fleet coordinates through shared git operations — no RPC, no message bus,
no service discovery. The repo IS the field.

### First-Person Time
Every commit has an author, a timestamp, and a parent. Each branch carries
its own history — that IS first-person subjective time. `git log --all`
is the aggregate timeline. `git diff` between branches IS the bearing rate.

### Death Is Default
An agent that stops pushing vanishes. `git branch -D` explicitly kills.
Pre-receive hooks reject stale pushes (TTL expired = dead). Silence IS
death. No central reaper needed — the field itself rejects the dead.

### Collision Detection
Two branches with converging heads and no merge in progress = collision.
`git merge-base` gives the point of closest shared ancestry.
`git rev-list --count` measures divergence. `git merge` IS collision resolution.
`git rebase` IS heading change.

### GitHub Is the PLATO Room Server
GitHub/remote bare repo = the central field where agents meet. Every push
triggers hooks. Every pull syncs state. GitHub Issues are mission reports.
GitHub Actions are lifecycle hooks. We didn't know we were building fleet
infrastructure — we were just using version control.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 FLEET REPO (bare)                │
│  refs/heads/                                    │
│    ├── scout-alpha          ← agent branch       │
│    ├── navigator-bravo      ← agent branch       │
│    └── harvester-charlie    ← agent branch       │
│  refs/notes/keel/agent/                          │
│    ├── scout-alpha          ← birth, TTL, heading│
│    ├── navigator-bravo      ← birth, TTL, heading│
│    └── harvester-charlie    ← birth, TTL, heading│
│  hooks/                                         │
│    ├── pre-receive           ← TTL enforcement   │
│    ├── update                ← per-ref TTL check │
│    └── post-receive          ← bearing logging   │
└─────────────────────────────────────────────────┘
```

### Map to Fleet Concepts

| Git Primitive | Keel Concept |
|---|---|
| `git init --bare` | Deploy the field |
| `refs/heads/<agent>` | Agent heading (branch) |
| `git commit` | Act / produce output |
| `git push` | Heartbeat |
| `git log --all` | Build record / fleet history |
| `git diff <a> <b>` | Bearing rate computation |
| `git merge-base` | Point of closest shared ancestry |
| `git merge` | Collision resolution |
| `git rebase` | Heading change |
| `git notes` | Agent metadata (birth, TTL, heading) |
| `git branch -D` | Death-as-default |
| `pre-receive` | TTL enforcement hook |
| `post-receive` | Bearing calculation hook |
| `git pull` | Synchronize with fleet state |
| No push for TTL seconds | Death (silence IS death) |

---

## Usage

### 1. Initialize the Fleet

```bash
./keel-git-init.sh /tmp/keel-fleet.git
```

Creates a bare repo with TTL hooks. All agents push here.

### 2. Launch an Agent

```bash
KEEL_HEARTBEAT=3 KEEL_TTL=30 ./keel-git-agent.sh scout-alpha /tmp/keel-fleet.git
```

Agent pushes every 3 seconds with a random heading. Dies after 30 seconds.

### 3. Monitor Bearings

```bash
# One-shot report
./keel-git-bearings.sh /tmp/keel-fleet.git

# Continuous watch
./keel-git-bearings.sh /tmp/keel-fleet.git --watch

# Only alerts (deaths, collisions)
./keel-git-bearings.sh /tmp/keel-fleet.git --alerts
```

### 4. Collision Exercise

```bash
# Terminal 1 — Terminal 2 — Terminal 3
KEEL_HEADING_CHANGE=0.01 KEEL_TTL=120 ./keel-git-agent.sh scout-alpha /tmp/keel-fleet.git
KEEL_HEADING_CHANGE=0.01 KEEL_TTL=120 ./keel-git-agent.sh navigator-bravo /tmp/keel-fleet.git
KEEL_HEADING_CHANGE=0.01 KEEL_TTL=120 ./keel-git-agent.sh harvester-charlie /tmp/keel-fleet.git

# Meanwhile:
./keel-git-bearings.sh /tmp/keel-fleet.git --watch
```

---

## The Keel Philosophy

### No Central Scheduler
The fleet self-organizes through git operations. Each agent knows its own
heading and pushes when it has something to say. There is no "controller"
telling agents when to act. The field IS the command.

### First-Person Termination
Each agent carries its own TTL in its git notes. Death is self-declared.
No external process needs to kill anything. If you stop pushing, you die.
If your TTL expires, pre-receive rejects your next push. The field enforces
the contract.

### Bearing Through Diff
Two agents don't need to talk directly to know each other's heading.
`git diff` between branches IS the bearing computation. `git log --all`
IS the aggregate state. Every agent can compute its relative position
to every other agent just by reading the field.

### Collision as Merge Opportunity
Collision is not an error — it's a merge opportunity. When two branches
converge, it means two agents found the same target. They should merge
their work. If they don't, the collision detection surfaces the risk.

### Silence IS Death
An agent that doesn't push for longer than its TTL is dead. No heartbeat
to terminate — just absence. Death is the default state. Life requires
continuous push. This maps to the fundamental truth: staying alive takes
work.

---

## Example: Three-Agent Fleet Run

```
Terminal 1: $ KEEL_TTL=30 KEEL_HEARTBEAT=3 \
                ./keel-git-agent.sh scout-alpha /tmp/keel-fleet.git
Terminal 2: $ KEEL_TTL=30 KEEL_HEARTBEAT=3 \
                ./keel-git-agent.sh navigator-bravo /tmp/keel-fleet.git
Terminal 3: $ KEEL_TTL=30 KEEL_HEARTBEAT=3 \
                ./keel-git-agent.sh harvester-charlie /tmp/keel-fleet.git
Terminal 4: $ ./keel-git-bearings.sh /tmp/keel-fleet.git --watch
```

Expected output after ~15 seconds:
```
=== Active Branches (Agent Headings) ===
  scout-alpha (age=2s)
  navigator-bravo (age=4s)
  harvester-charlie (age=3s)

=== Headings ===
  scout-alpha → hdg-a1b2c3d4|142|7
  navigator-bravo → hdg-e5f6g7h8|271|3
  harvester-charlie → hdg-i9j0k1l2|045|9

=== Bearing Rates & Collision Detection ===
  scout-alpha <-> navigator-bravo: divergence=6c (a:3c, b:3c)
  scout-alpha <-> harvester-charlie: divergence=6c (a:3c, b:3c)
  navigator-bravo <-> harvester-charlie: divergence=6c (a:3c, b:3c)
```

After ~31 seconds, all three agents die (TTL=30). Branches become stale.
Pre-receive would reject any new push. The fleet is quiet.

---

## Extensions

### Real Headings
Replace the random heading generator with actual data:
- Compass heading from a vessel
- GPS track vector
- Fleet objective vector (waypoint bearing)
- Market direction from a trading signal

### Weighted Bearings
Use `git notes` to carry weight/mass/priority. Closer bearing + higher
mass = priority collision to resolve.

### Agent Deletion
An agent can self-delete by pushing a branch deletion:
```bash
git push origin :scout-alpha
```

### Merge Protocol
When collision is detected, the bearing tool can suggest:
```bash
git merge scout-alpha navigator-bravo -m "collision resolution: both found target X"
```

---

## Requirements

- **git** (any version 2.x)
- That's it. No packages. No daemons. No databases. No message queues.
- **Bash** for the scripts, but the patterns work in any language.

Git already IS your fleet infrastructure. You just didn't know it.
