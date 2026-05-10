# Keel on NATS — Death as Default Transport

**Architectural insight: NATS ALREADY HAS BUILT-IN TTL.**
Every message has a max age. Subjects are channels (like PLATO rooms).
Queue groups are agent pools. NATS's design philosophy — "at most once
delivery, no persistence by default" — IS death-as-default for messages.

## The Core Insight

The Keel TTL Engine doesn't need a central scheduler. It doesn't need
a death-watch daemon. It doesn't need explicit cleanup.

**NATS was designed for this.**

Each message carries its own death via the `Nats-Msg-Timeout` header.
Subjects ARE the room protocol. Queue groups ARE agent pools. The broker
enforces TTL at the transport layer.

We're not adding TTL to NATS — we're discovering that NATS was already
the Keel transport protocol.

## Subject Mapping

| Subject | Purpose |
|---------|---------|
| `keel.agent.{id}.heading` | Agent heading (position + velocity + intention) |
| `keel.agent.{id}.heartbeat` | Short-TTL liveness signal |
| `keel.bearing.{a}.{b}` | Computed bearing between two agents |
| `keel.trust.{subject}` | Decaying trust assertions |
| `keel.tile.{room}` | PLATO-style tile storage (JetStream) |
| `keel.collision.{a}.{b}` | Auto-published collision warnings |

## TTL Architecture

- **Heading TTL**: 30s default — message dies if agent stops publishing
- **Heartbeat TTL**: TT/4 (7.5s) — liveness dies fast
- **Bearing TTL**: min(source TTLs) — bearings die with their inputs
- **Trust decay**: per-assertion — no explicit revocation
- **JetStream max_age**: 1h — tiles auto-expire at storage level
- **Collision TTL**: 5s max — urgent, perishable warnings

## Death-as-Default Pattern

```
Agent publishes heading → TTL header set → broker auto-expires if unsubscribed
Agent goes silent       → no messages → broker just stops delivering
Cleanup?               → None needed. Death. Is. Default.
```

## Files

- `keel_nats.py` — Pure Python library (nats-py). Contains:
  - `KeelAgent` — lifecycle: publish heading + heartbeat with TTL
  - `BearingWatcher` — listens on `keel.agent.*.heading`, computes bearings
  - `CollisionDetector` — listens on `keel.collision.>`, risk assessment
  - `TileStore` — JetStream-backed PLATO tile storage
  - `TrustRegistry` — decaying trust assertions
  - `KeelNATS` — top-level orchestrator

- `demo.py` — 3-agent scenario showing:
  - Circle movement (safe baseline)
  - Crossing trajectories (collision risk)
  - Real-time bearing computation
  - Automatic collision warnings
  - Self-terminating data via TTL

## One-Line Agent

```bash
nats reply keel.agent.demo.heading \
  '{"agent_id":"demo","position":{"x":0,"y":0},"velocity":{"vx":0.3,"vy":0.01},"intention":"cruising","status":"active","ttl":30}' \
  --header "Nats-Msg-Timeout: 30"
```

One line. One agent. Self-terminating in 30 seconds. No scheduler required.

## Running

```bash
# Terminal 1: Start NATS
nats-server

# Terminal 2: Run demo
cd /tmp/keel-models/nats
python3 demo.py

# Terminal 3 (optional): Watch all Keel traffic live
nats sub "keel.>" --header
```
