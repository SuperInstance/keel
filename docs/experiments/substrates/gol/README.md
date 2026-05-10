# Keel TTL Engine — Conway's Game of Life as Coordination Substrate

> *The Game of Life proves the architecture. 75% of cells die by default.
> Life is active maintenance. Local rules produce global coordination.
> There is no scheduler. There is only the field.
> **Keel is Conway's Game of Life for agent fleets.** *

---

## The Coordinated Cell

Conway's Game of Life has three properties that make it the purest
embodiment of Keel's TTL (Time-To-Live) coordination model:

| Life Property | Keel Equivalent |
|---|---|
| Local rules (8 neighbors) | Local bearing-rate coordination |
| No central scheduler | The field IS the command |
| Death is default | Every agent has a TTL |
| Birth requires 3 neighbors | New tiles need consensus |
| Structures emerge from rules | Fleet behavior from agent rules |

**In a random initial state, ~75% of cells die immediately.**
This is not a bug. This is the architecture. Death is the default.
Life — sustained existence — is active maintenance against entropy.

---

## The Five TTL Types as Cellular Automata

### TileTTL — Block Pattern (BIRTH → LIVE → DIE)

**Life pattern:** 2×2 block (the simplest stable Life structure)

A cell is born with a fixed lifetime counter. Each generation decrements
the counter. When it hits zero, the cell dies — regardless of its neighbors.

Every tile is temporary. The block persists for N generations, stable and
unchanging, then vanishes without a trace. No death spiral, no decay.
Just: done.

> *"A tile holds its shape for exactly as long as it needs to, then
>   releases. No lingering. No attachment."*

---

### TaskTTL — Glider (Move then die)

**Life pattern:** Glider (the iconic Conway pattern that travels diagonally)

The glider follows standard Conway B3/S23 rules: it moves across the grid,
maintaining its shape through neighbor interactions. The moment any cell
of the glider touches a boundary, ALL cells die immediately.

The task doesn't fade. It works until it reaches its edge, then it's done.
Edge detection is termination. The boundary IS the TTL.

> *"A task crosses the field, reaches the edge, and is done.
>   No teardown. No graceful shutdown. Just: edge hit = complete."*

---

### AgentTTL — Oscillator (Survive through output)

**Life pattern:** Blinker oscillator (3 cells oscillating between two states)

Modified Conway: survival requires at least 2 neighbors. A cell with only
1 neighbor is considered "silent" and dies, even though standard Conway
would let it survive.

This maps to agent viability: an agent that touches no one, that produces
no output, that has no connections — dies. Silence is death.
Output is survival. Connection is life.

> *"An agent with no neighbors is not an agent. It's a rock.
>   Agents communicate. Agents output. Silence = death."*

---

### BearingTTL — Two Gliders (Compute bearing angle)

**Life pattern:** Two gliders on intersecting paths

Two labeled clusters (1 = ○, 2 = ●) move across the grid. At each
generation, we compute each cluster's centroid and derive its movement
vector from the last two positions. The angle between these vectors is
the **bearing** between the two clusters.

This is pure bearing-rate coordination: two entities moving through the
same field, computing their relationship from their local paths alone.
No central tracker. No messaging. Just: trajectory reveals intent.

> *"The field reveals relationships. Two agents move.
>   The angle between their paths IS their coordination signal."*

---

### TrustTTL — Replicator (Propagate with decay)

**Life pattern:** Pattern that replicates, each copy smaller

Cell values represent "trust level" (5 = high, 1 = low). A cell with
trust T spawns new cells with trust T-1. Each propagation hop reduces
trust. The pattern spreads outward like a rumor, a recommendation, or
a credential chain — but each hop is weaker.

When trust reaches 1 and the pattern can no longer sustain, it dies.
Trust doesn't last forever. Propagation is exponential decay.

> *"Trust propagates through the network, decaying with each hop.
>   First-hand trust is 5. Second-hand is 4. By the fifth hop,
>   you barely know the source. Trust has a TTL."*

---

## Running the Demo

```bash
python3 /tmp/keel-models/gol/demo.py
```

All five automata run simultaneously, side by side, updating every 0.5s.
Press Ctrl+C to stop early.

Each grid shows:
- **TileTTL** (top-left): 2×2 block counting down its lifetime
- **TaskTTL** (top-center): Glider crossing the grid toward the edge
- **AgentTTL** (top-right): Blinker oscillating (or dying without neighbors)
- **BearingTTL** (bottom-left): Two gliders with bearing angle display
- **TrustTTL** (bottom-right): Diamond pattern propagating and decaying

---

## The Architecture

```
        CONWAY                     KEEL
        ──────                     ────
  75% die at birth         →   75% of agents reject on spawn
  3 neighbors = birth      →   3 votes = consensus
  Glider hits edge = dead  →   Task reaches scope = done
  Block = stable forever   →   Tile = temporary by design
  Oscillator = sustained   →   Agent = needs output to live
  Pattern interaction      →   Bearing = coordination signal
  Replicator = growth      →   Trust = propagates, decays
```

**There is no scheduler.**
There is only the field. The grid. The neighbors.

Every cell evaluates its own rules, looks at its own neighbors,
computes its own fate. No cell issues commands. No cell stores
a global state. The behavior of the whole emerges from the rules
of each part.

This is the Keel architecture. This is how agent fleets coordinate.

> *"We don't command the field. We set the local rules and let the
>   coordination emerge. Just like Conway. Just like Life."*

---

## File Structure

```
/tmp/keel-models/gol/
├── keel_gol.py    # Core implementation: Grid, all 5 rule classes, renderers
├── demo.py        # Demo: runs all 5 automata simultaneously
└── README.md      # This file — the philosophy
```
