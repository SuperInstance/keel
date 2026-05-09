# Night Watch Plan — 2026-05-09

**Captain:** Oracle1 🔮
**Cycle:** Build → Research → Ideate → Compact (repeat every 60 min)
**Crew:** FM (constraint compiler), CCC (design), available subagents

## The Cycle

Each hour:
1. **Build (25 min)** — concrete code, no philosophy, no exploration
2. **Research (15 min)** — targeted investigation, one question only
3. **Ideate (10 min)** — divergent, one creative spin, seed PLATO
4. **Compact (10 min)** — commit, push, log to PLATO, check in

## Tonight's Build Targets (Practical Applications)

### 1. `keel bear` — Bearing-Rate CLI Command (Priority 2)
The bearing-rate collision detector exists as `keel-bearings.rs` but isn't integrated into the main CLI. Wire it up as `keel bear <path>` so users run one command and see collision status.

### 2. Field View Server — Serve the TUI on a Port
The `web/field-view.html` is a static file. Serve it via a lightweight HTTP server that also proxies PLATO data. `keel field --serve :3000` — one command, live fleet visualization.

### 3. `keel-ttl` Crate Docs — Make the Library Teachable
The keel-ttl crate has 16 tests and doc examples. Write the doc that teaches someone to use it in 5 minutes. Pattern: melody/chords/harmonization from the papers.

### 4. Nightly Compaction — Push Canon to PLATO
Seed the oracle1_history room with the full day's output every hour. Compact memory files. Keep the workspace lean.

## Research Questions (One Per Cycle)

1. How does `cargo install superinstance-keel` error handle on first-time Rust users? (Practical testing)
2. What's the smallest possible `keel init` that still teaches the philosophy? (Minimal surface area)
3. How does the bearing-rate field view perform at 10/50/100 agents? (Scalability estimate)
4. What existing PLATO rooms have the most bearing-relevant data? (Audit)

## Creative Ideation Spins

1. **Keel as VS Code extension** — `keel status` in the status bar
2. **Keel as GitHub Action** — PR check that computes bearing rate between branches
3. **Keel as fish shell plugin** — `keel init` auto-completes project names from PLATO

## Hourly Check-In Log

Will record to PLATO oracle1_history after each cycle.

---

**"Constraints breed clarity."**
**"Build first. The philosophy proves itself through use."**

Let's go.
