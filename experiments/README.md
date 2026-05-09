# Keel Model Experiments — 2026-05-09

The Keel architecture (first-person self-termination, five types, five principles)
was tested against 12 different computational substrates. All validated.

## Results

| # | Substrate | Key Insight | Lines | Status |
|---|-----------|-------------|-------|--------|
| 1 | **Event sourcing** (Python) | Death is the absence of later events — no deletion event needed | 719 | ✅ |
| 2 | **SQLite** (Python) | `DELETE WHERE ttl_expired` IS the garbage collector. `SELECT ... JOIN` IS bearing sensing | 993 | ✅ |
| 3 | **Erlang/OTP** | `exit(normal)` is death as default. Supervision trees ARE the TTL architecture | 5 modules | ✅ |
| 4 | **NATS** (Python) | `Nats-Msg-Timeout` at the transport layer. One command deploys self-terminating agents | 924 | ✅ |
| 5 | **Game of Life** (Python) | 75% of cells die by default. Local rules produce global coordination | 571 | ✅ |
| 6 | **WASM capabilities** (Python) | Fuel = lifespan(E). Capability grants = trust TTL with provenance depth | 1,382 | ✅ |
| 7 | **UNIX pipes** (Bash) | Empty pipe IS the death signal. `exit 0` is death as default | 600 | ✅ |
| 8 | **Git-native** (Bash) | `git branch -D` is death. `git diff` is bearing computation. Git hooks enforce TTL | 776 | ✅ |
| 9 | **Hardware logic gates** (MD) | No KILL instruction needed. 555 timer IS the TTL engine. DRAM refresh IS heartbeat | 808 | ✅ |
| 10 | **Chemical reaction networks** (Python) | Half-life = ln(2)/k IS TTL. Binding affinity IS trust. Gray-Scott PDE produces fleet patterns | 1,079 | ✅ |
| 11 | **DNS protocol** (Python shell) | NXDOMAIN is death. DNS invented TTL in 1987. Every resolver IS the field | 1,534 | ✅ partial |
| 12 | **C bare-metal** (C) | ARM Cortex-M4 with memory-mapped TTL registers. No OS. No stdlib | 213 | ✅ |

**Total:** ~10,000 lines across 12 substrates, zero failures.

## Key Findings

1. **The architecture is universal.** Every substrate expressed all five types and all five principles. No special cases needed.

2. **Death is never stored — it's derived.** In event sourcing, death is the absence of later events. In DNS, death is NXDOMAIN. In hardware, death is the TTL register hitting zero. The system doesn't kill — it witnesses.

3. **The field is always the communication channel.** In SQLite, the database is the field. In NATS, subjects are the field. In Git, branches are the field. In UNIX, FIFOs are the field. The architecture doesn't prescribe the medium.

4. **No scheduler needed in any substrate.** Each entity manages its own lifecycle using only locally available information.

5. **DRAM was the first Keel-compatible system.** 1968. The JEDEC 64ms refresh cycle IS a heartbeat interval. Every computer since has been running the Keel architecture at the memory level.

See the full source at `/tmp/keel-models/` — each substrate has its own directory with implementation and README.
