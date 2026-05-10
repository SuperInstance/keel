# Keel TTL Engine — Erlang/OTP

> "Erlang got it right in 1986. We're just noticing that OTP is the TTL
>  architecture expressed as framework semantics. `exit(normal)` is death
>  as default."

## The Philosophical Match

The Keel TTL Engine embodies _first-person self-termination_: every entity
carries its own death from its own frame. No central scheduler decides when
things die. Death is default — existence requires continuous effort.

Erlang/OTP's supervision trees **are** this architecture:

| Keel Concept            | OTP Mechanism                                                |
|-------------------------|--------------------------------------------------------------|
| Self-termination        | `gen_server:stop/1` — a process stops itself                 |
| Death as default        | `exit(normal)` — terminating is the natural state            |
| Supervisor as scheduler | `supervisor` — decides restart strategy on death             |
| Restart strategies      | `one_for_one`, `one_for_all`, `rest_for_one`                 |
| Restart intensity       | MaxR + MaxT — supervisor dies if too many children die       |
| Hierarchical TTL        | Supervisor trees — tiles under subsupers under chief         |

## What's Here

```
keel_ttl.erl         — 5 gen_server types, each self-terminating
keel_bearings.erl    — ETS-based bearing registry (field communication)
keel_sup.erl         — Supervision tree (configurable strategy)
keel_sup_chief.erl   — Top-level supervisor (one_for_all)
keel_app.erl         — OTP application entry point
README.md            — This file
```

### The Five TTL Types

**1. `tile_ttl`** — Fixed TTL timer. Die after N seconds.
```erlang
{ok, Pid} = keel_ttl:start_link(tile_ttl, 30).  %% 30s self-termination
```

**2. `task_ttl`** — Staleness timer. Heartbeats reset the clock. Silence = death.
```erlang
{ok, Pid} = keel_ttl:start_link(task_ttl, 10).   %% 10s staleness
gen_server:cast(Pid, {heartbeat}).                 %% resets timer
```

**3. `agent_ttl`** — Output IS heartbeat. If no output produced within a
silence window, the agent dies. Periodic check, not a timer-based approach.
```erlang
{ok, Pid} = keel_ttl:start_link(agent_ttl, ok).
gen_server:cast(Pid, {output, some_data}).         %% keeps agent alive
```

**4. `bearing_ttl`** — Collision detection. Registers a heading with the
bearing registry. If another process at the same heading is within a speed
proximity, collision is detected and the process dies.
```erlang
{ok, Pid} = keel_ttl:start_link(bearing_ttl, {north, 10}).
```

**5. `trust_ttl`** — Trust decays. No explicit revocation possible. Trust
erodes over time until the entity naturally dies.
```erlang
{ok, Pid} = keel_ttl:start_link(trust_ttl, {0.9, 0.01}).
%% 0.9 initial trust, 0.01 decay/tick → ~89 ticks to death
```

## Running

```bash
# Compile
cd /tmp/keel-models/erlang
erlc *.erl

# Run tests
erlc -DTEST *.erl && erl -noshell -eval "eunit:test([keel_ttl, keel_bearings, keel_sup], [verbose])" -s erlang halt

# Start the application
erl -noshell -eval "application:start(keel_app)" -s erlang halt
```

## Architecture

```
keel_sup_chief (one_for_all)
├── keel_sup (one_for_one)     ← independent tiles
├── keel_sup (one_for_all)     ← tightly-coupled tiles
└── keel_sup (rest_for_one)    ← dependent chain tiles
```

Each `keel_sup` manages any number of child processes via `start_child/1`.

When a `tile_ttl` process dies (`exit(normal)` after TTL expiry), the
`keel_sup` decides whether to restart it based on the configured strategy:

- **transient restart** — Only restart on abnormal exit. `exit(normal)` stays dead.
  This means natural TTL expiry = permanent death, which IS the correct TTL behavior.
  Abnormal crashes (bugs, resource exhaustion) get restarted.

## The Field: Bearings

`keel_bearings` implements a shared bearing field using ETS. Processes
register their heading. Any process can read any heading. No message
passing required for reading. This is tuple-space communication applied
to vessel/agent location tracking.

```erlang
keel_bearings:register(Pid, north, 10).
{ok, {north, 10}} = keel_bearings:get_heading(OtherPid).
keel_bearings:detect_collision(Pid, north, 10).
```

## Why Erlang/OTP for TTL

Traditional TTL systems are centralized: a scheduler pings entities, checks
timestamps, and kills stale ones. This is third-person death — something
external does the killing.

Erlang/OTP inverts this:

1. **Processes kill themselves.** The timer is internal. `exit(normal)` is
   the entity's own decision to die.

2. **The supervisor reacts, not schedules.** It doesn't check if children
   are alive. It receives `{'EXIT', Pid, Reason}` messages from the runtime.
   Death is an event, not a poll result.

3. **Hierarchical death.** A supervisor that exceeds its restart intensity
   also dies, propagating the failure upward. This means the system has
   thermal limits built into its structure.

4. **`transient` restart is TTL-native.** A tile that times out normally
   stays dead. A tile that crashes gets restarted. The framework
   distinguishes between natural death and system failure — exactly the
   semantics Keel needs.

> "OTP doesn't implement TTL. OTP **is** TTL, expressed as process
>  lifecycle semantics written 30 years ago."

## License

Part of the Keel architecture — first-person self-termination for distributed
systems. Do what you want with it.
