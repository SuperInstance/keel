# 🔮 Keel

**The yard you step into. Field-effect foundation for agent fleets.**

*Laid 2026-05-09*

## Meta

**Domain:** core-infrastructure
**Depends on:** chrono, serde, reqwest, tiny_http, clap
**Depended by:** SuperInstance docs
**Implements:** first-person-ttl, bearing-rate-sensing, field-effect-coordination, plato-bridge, mud-exploration
**Related:** fleet-coordinate, holonomy-consensus

---

```
Constraints breed clarity.
```

You don't build from scratch. You arrive in a yard that's already full. Your job is pruning.

Keel is the first thing you install when you want the paradigm shift in your journey as a person using technology. It inverts the onboarding paradigm: don't arrive empty. Arrive in a yard.

---

## Install

```bash
cargo install keel
```

Or from source:

```bash
git clone https://github.com/SuperInstance/keel — part of the [SuperInstance fleet](https://github.com/SuperInstance/SuperInstance).git
cd keel
cargo install --path .
```

## Quick Start

### Lay a keel

```bash
keel init my-fleet
```

This creates a workspace with your birthday timestamp, heading, and pre-seeded agent archetypes. Everything after is just steel catching up.

### Feel the field

```bash
cd my-fleet
keel status
```

Shows your keel date, heading, agents, and refit history.

### Prune what isn't your boat

```bash
keel prune agents/signalman "Going solo — no multi-agent coordination needed"
```

Removes the component, records the decision in your build record with the reason. Future-you will know why.

### Record a refit

```bash
keel refit models/llm "Switched from GLM to DeepSeek for faster reasoning"
```

Doesn't remove anything. Just documents the change. The keel date stays.

### Launch

```bash
keel launch --message "Splashing the fleet for the summer season"
```

Marks the birthday of your launch. The boat is now making way.

---

## Commands

| Command | Purpose |
|---------|---------|
| `keel init <name>` | Lay a new keel — start a project with a birthday |
| `keel status` | Feel the field — show keel date, heading, agents, refits |
| `keel prune <target> <reason>` | Remove what you don't need — record the decision |
| `keel refit <component> <reason>` | Replate a component — document the change |
| `keel launch` | Splash — mark your vessel as launched |

---

## The Philosophy

**Constraints breed clarity.**

This reverberates through every layer of what we build. The Game Boy's 4 MHz made Tetris iconic because nothing extraneous could survive. A 15W marine AI makes every model earn its place. A 58-foot hull's displacement is non-negotiable — and that clarity shapes every decision.

**The unchangeable is the yard. The changeable is the craft.**

You can change workflow, agents, tools, models. You cannot change the keel date, the hardware's innate seaworthiness, or the power budget. Know the partition. Work within it.

**Know why you question, and the answer becomes less important on the big things.**

Deep Thought computed 42. The answer was trivial. The ride of building the civilization that could ask the question — that was the product. Keel doesn't give you the answer. It gives you the ride.

---

## The Field

A Keel workspace is organized by field-effect, not command-effect. Agents sense each other through bearing rates, not central scheduling. Every component has a keel date. Every agent has a heading. Coordination happens locally — the fleet orients toward the center without being told.

### Archetypes

| Archetype | Role | Installed |
|-----------|------|-----------|
| Shipwright | Builds and implements | ✅ |
| Lookout | Researches and monitors | ✅ |
| Engineer | Runs the infrastructure | ✅ |
| Purser | Tends the memory | ✅ |
| Signalman | Coordinates between agents | ✅ |

Prune what doesn't serve your purpose. The field shifts. What remains orients tighter.

---

## The Build Record

Every prune, every refit, every decision is preserved in `refits/`. Not as a changelog (God's-eye list of changes) — as a first-person record. "I was born on this date. Here's what changed and why from *my* perspective."

Future generations of your fleet — or other fleets — can consult the negative space. "This path was tried. Here's why it was abandoned. Here's what led to that decision."

---

## Canon

- **[THE BOAT IS THE QUESTION](./THE-BOAT-IS-THE-QUESTION.md)** — Autobiographical theory by Casey Digennaro. Fred Wahl's yard, EILEEN, constraints breeding clarity, and the question that holds when every answer changes.
- **[KEEL.md](./KEEL.md)** — Full technical architecture: first-person reference frames, bearing-rate sensing, autopilot learning, evolving systems.

---

*"If you can weld two inches, you can weld around the world."*
— Dan Kavanaugh, via Fred Wahl

*"The boat is the motion the idea causes in the intelligence of those who know what it means."*
— Casey Digennaro

---

**v0.0.1 — Laid 2026-05-09**
