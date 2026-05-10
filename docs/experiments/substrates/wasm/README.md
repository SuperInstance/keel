# Keel TTL Engine — WASM Component Model

> WASM components are Keel agents. Fuel is the unified equation: lifespan = f(use, load, time). When fuel runs out, the component halts — no orchestrator killed it, no garbage collector reaped it. Capabilities are trust TTL — they decay, must be renewed, are bounded by provenance depth. The runtime IS the field. The component model IS the architecture.

---

## The Mapping

| WASM Concept | Keel Concept | Why It Fits |
|---|---|---|
| **Component** | Agent | Each component is a self-contained unit with explicit imports/exports, bounded resources, and a single entry point |
| **Interface (WIT)** | Bearing protocol | WIT defines exactly what an agent can observe and expose — the bearing between agents |
| **Fuel / resource limits** | lifespan(E) | Each component has a max fuel budget. When depleted, the component halts. Death is default. |
| **Capability-based security** | Trust TTL | Capabilities are unforgeable tokens with expiry. They decay like trust, must be renewed, and cannot be escalated. |
| **World** | The field | The world definition binds a component to its runtime environment with explicit import requirements |

## The Five Principles

### 1. Tiles have TTL (data death)

Every data structure carries its own death clock. A `tile` has `keel-date` (birth) and `ttl-ms` (lifespan). After `keel-date + ttl-ms < now`, the tile is dead — the runtime garbage collects it automatically.

**WASM analogy:** Memory pages with bounded allocation lifetimes.

### 2. Agents have TTL (agent death)

Every agent component has a fuel budget = lifespan. Each invocation consumes fuel. When fuel reaches 0, the component cannot be called — death is the default state. No external orchestrator killed it.

**WASM analogy:** Component fuel limits. When fuel is exhausted, the component halts naturally.

### 3. Bearings have TTL (observation decay)

An agent's observation of another agent has its own death clock. A bearing contains `observed` (timestamp) and `ttl-ms`. After the TTL, the bearing is stale — collision risk defaults to `stable` (no data).

**WASM analogy:** Component interface calls carry a freshness timeout. Stale responses are discarded.

### 4. Trust has TTL + depth (confidence decay)

A trust assertion has `confidence`, `depth` (provenance chain length), and `ttl-ms`. Effective confidence decays as TTL expires: `confidence * (1 - elapsed/ttl_ms)`. A trust claim that's fully expired has 0% effective confidence.

**WASM analogy:** Capability expiry. A capability grant that's fully expired cannot be used — the component literally cannot access the resource.

### 5. Capability = Trust TTL (the identity)

Capabilities and trust TTL are the same thing:

- **Capabilities are granted**, not ambient — each grant has an expiry
- **Capabilities decay** automatically — expired capabilities are unreachable
- **Capabilities must be renewed** — the grantor re-issues before TTL expiry
- **Capabilities cannot be escalated** — a component cannot create capabilities it doesn't hold
- **Provenance depth** — a capability granted by A to B, then by B to C has depth 2. Effective trust in that capability decays with depth.

This is _not_ a metaphor. In a real WASM implementation, the capability store is a WASM component with `grant`, `revoke`, and `has` exports. The runtime enforces capability checks before every resource access.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    keel.wit                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  keel-ttl   │  │ fuel-budget  │  │ cap-store │  │
│  │  interface  │  │  interface   │  │ interface │  │
│  └──────┬──────┘  └──────┬───────┘  └─────┬─────┘  │
│         │                 │                 │        │
│         └──────────┬──────┴─────────┬──────┘        │
│                    │                │                │
│            ┌───────▼────────────────▼───────┐       │
│            │     world keel-agent           │       │
│            │  ┌─────────────────────────┐   │       │
│            │  │ import keel-ttl;        │   │       │
│            │  │ import fuel-budget;     │   │       │
│            │  │ import capability-store;│   │       │
│            │  │ import plato-storage;   │   │       │
│            │  │ export run: func()->str;│   │       │
│            │  └─────────────────────────┘   │       │
│            └────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                   keel_runtime.py                    │
│                                                      │
│  ┌────────────┐   ┌─────────────┐   ┌───────────┐   │
│  │  Registry  │   │ Fuel Budget │   │ Cap Store  │   │
│  │   (field)  │──▶│ (lifespan)  │──▶│ (trust)    │   │
│  └────────────┘   └─────────────┘   └───────────┘   │
│         │                                            │
│         ▼                                            │
│  ┌──────────────────────────────────────────────┐    │
│  │  Agent Components                             │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐      │    │
│  │  │ leader   │ │ follower │ │ scout    │      │    │
│  │  │ fuel:50k │ │ fuel:20k │ │ fuel:5k  │      │    │
│  │  │ caps:6   │ │ caps:3   │ │ caps:2   │      │    │
│  │  └──────────┘ └──────────┘ └──────────┘      │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  GC: ✂️ Expired capabilities  ✂️ Dead agents        │
│      ✂️ Expired tiles                                │
└─────────────────────────────────────────────────────┘
```

---

## Running the Demo

```bash
# Show component generation and TTL patterns
python3 /tmp/keel-models/wasm/keel_component.py

# Run the runtime with the convoy scenario
python3 /tmp/keel-models/wasm/keel_runtime.py
```

Expected output from `keel_runtime.py`:

```
── Tick 1 ──
  leader: leader:executed
    fuel: 45.0/50.0 (10% consumed)
  follower: follower:executed
    fuel: 16.0/20.0 (20% consumed)
  scout: scout:executed
    fuel: 2.0/5.0 (60% consumed)
  leader trust: 'heading=north-by-northeast' eff_conf=0.950
  follower bearing → leader: risk=stable
  scout tile: tile:scout:0

[... ticks progress ...]

── Tick 3 ──
  scout: COMPONENT_DEAD:scout         ← Death is default
    fuel: -1.0/5.0 (120% consumed)

[... GC reclamation ...]

FINAL STATE
  Agent(leader, fuel=10.0/50.0, caps=6, heading='north-by-northeast')
  Agent(follower, fuel=4.0/20.0, caps=3, heading='follow-leader')
  Live tiles: 0
  Events logged: 22

  ✓ Scout correctly died (death is default)
  ✓ Fuel depletion is natural termination
  ✓ Capabilities decay with time
  ✓ No orchestrator killed anything — fuel budget is life
```

---

## Files

| File | Purpose |
|---|---|
| `keel.wit` | WIT interface definition — the contract all Keel components implement |
| `keel_component.py` | Component stub generator + TTL type definitions |
| `keel_runtime.py` | Minimal WASM-like runtime with fuel, capabilities, GC |
| `README.md` | This file |

---

## Real WASM Impl Notes

To make this real (WASI preview 3 + component model):

1. **Compile WIT**: `wit-component` generates bindings from `keel.wit` in Rust/C
2. **Component adapter**: Each Keel agent is a WASM component compiled with `wasm-tools component new`
3. **Fuel tracking**: WASI preview 3 supports `fuel` via `wasmtime` — set initial fuel per component instance
4. **Capability store**: Implement as a host-provided WASM component that agents import
5. **PLATO storage**: Implement as a host-provided WASM component with capabilities gating access
6. **GC**: The runtime monitors fuel, active capability TTLs, and tile TTLs — on GC tick, it drops dead components and expired data

The core insight holds: **WASM components ARE Keel agents. The component model IS the TTL architecture. The runtime IS the field.**
