# Keel

You just walked into a shipyard. There's sawdust in the air and steel underfoot. A foreman looks up from his drawings and hands you a tool. Doesn't explain. Doesn't tutorial. Just hands it over. This is that tool.

`keel` is a Rust CLI for managing agent fleet projects from first principles. You lay a keel — it stamps a birthday on your workspace and seeds it with agent archetypes. Everything after is steel catching up. No frameworks. No platforms. Nine commands that do exactly what they say.

```bash
cargo install superinstance-keel
keel init
keel status
keel bear
keel field
keel sync
```

The philosophy lives in the constraints: you can change your workflow, your agents, your models. You cannot change the day you were born or the power budget of the hardware. `keel` enforces that partition by recording every decision from the inside — not as a changelog, but as a first-person build record. Future-you opens `refits/` and knows exactly why the signalman was cut loose.

## The Nine Commands

| Command | What it does |
|---------|-------------|
| `init`  | Create a new fleet workspace with config and room directory |
| `status`| Connect to PLATO and show fleet health (98 rooms, 9,468 tiles) |
| `bear`  | Sense the field — report bearings of nearby agents |
| `field` | Show the topology graph of all rooms |
| `probe` | Discover a room's capabilities and contents |
| `prune` | Remove stale tiles and dead agents from a room |
| `refit` | Update a room's configuration |
| `launch`| Deploy a new agent to a room |
| `sync`  | Push and pull tiles from PLATO |

## Quick Start

```bash
cargo install superinstance-keel
keel init
keel status    # Connect to PLATO, see the fleet
keel bear      # Sense nearby agents
keel field     # Show room topology
keel sync      # Share knowledge
```

## License

Apache 2.0 — Cocapn fleet infrastructure.
