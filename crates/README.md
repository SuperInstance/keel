# keel-ttl

### First-person self-termination types for agent fleets.

`cargo add keel-ttl`

---

*Every entity carries its own death from its own frame. Death is default.
Survival must be actively earned. No central scheduler. No garbage collector.*

---

## Melody — 30 Seconds

```rust
use keel_ttl::*;
use chrono::Duration;

let tile = TileTtl::new("hello", Duration::hours(1));
assert!(tile.is_alive());
// After 1 hour: tile.is_alive() returns false.
// No garbage collector needed. The tile knows when to die.
```

Five types, one pattern: `{ birth, ttl }` + a status method.

## Chords — The Five Types

### TileTtl — Self-expiring memory

```rust
let tile = TileTtl::new("temperature: 22.4", Duration::minutes(5));
assert!(tile.is_alive());
println!("Data: {:?}", tile.data()); // Some("temperature: 22.4")
// After 5 minutes: data() returns None. Tile is invisible.

// Filter active tiles in one call:
let active = TileTtl::filter_active(&[tile]);
```

### TaskTtl — Self-expiring work

```rust
let mut task = TaskTtl::new(
    vec!["step1".into(), "step2".into()],
    Duration::seconds(30),
);
let completed = task.execute_until_stale();
// If all steps complete before 30s: completed == 2
// If not: stopped at the step where staleness was detected.
// No scheduler cancelled this task. It cancelled itself.
```

### AgentTtl — Self-expiring presence

```rust
let mut agent = AgentTtl::new("researching", Duration::hours(1));
assert!(agent.is_present());

// Output IS the heartbeat. No health checks.
agent.heartbeat();  // Reset the output window

// After Duration::hours(1): agent is expired.
// After Duration::minutes(15) without heartbeat: agent is absent.
// Silence IS death.
```

### BearingTtl — Self-expiring relationships

```rust
use keel_ttl::Risk;

let bearing = BearingTtl::new("agent-b", 0.5, 0.1, Duration::minutes(5));
assert_eq!(bearing.collision_risk(), Risk::Stable);

// If bearing is constant and heading overlaps:
//   collision_risk() returns Risk::Warning
// If bearing TTL expired:
//   collision_risk() returns Risk::Critical ("position unknown")
```

### TrustTtl — Self-expiring assertions

```rust
let trust = TrustTtl::new("verified proof", 0.95, 0, Duration::days(30));
assert!(trust.is_trusted());  // effective_confidence >= 0.7

// Trust decays linearly over 30 days.
// Provenance: each hop halves confidence.
// No certificate revocation list. No central authority.
```

## Harmonization — The Unified Equation

All five types follow the same law:

```
lifespan(E) = f(use(E), load(E), time(E))
Termination when: lifespan(E) < time(E)
```

- `use(E)` = how often the entity is referenced
- `load(E)` = environmental pressure
- `time(E)` = age from the entity's own first-person frame

This equation was discovered, not invented. It appears in IP networking (TTL, 1981), cell biology (apoptosis, 1972), neuroscience (synaptic pruning, 1949), nuclear physics (half-life, 1902), economics (price discovery, 1776), microbiology (quorum sensing, 1994), and machine learning (dropout, 2014).

The five types are the equation, voiced in five different keys.

## The Mandelbrot Constraint

Same types compile on Arduino and A100. Only the anchor density changes with scale.

See the full [architecture paper](https://github.com/SuperInstance/keel) for the complete philosophy.

---

**16 tests. 450 lines. Zero unsafe. No external deps beyond chrono.**

`cargo add keel-ttl`

*"Death is default. Survival must be actively earned."*
