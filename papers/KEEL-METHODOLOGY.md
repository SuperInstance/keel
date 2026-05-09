# The Keel Methodology
## A Practice-Based Introduction to First-Person Agent Systems

**What this is:** A tutorial. Not a sales pitch. Not a doctrine. A sequence of practices that, if followed, will lead you to the same architectural understanding the authors reached. Questions that arise during practice are answered by subsequent practice. This is not accidental.

**Prerequisites:** A terminal, cargo, and the willingness to sit with a problem before looking for the answer.

---

### Practice 1: Install the Yard

```bash
cargo install superinstance-keel
keel init first-vessel
cd first-vessel
```

Look at what was created. Notice the `keel_date` in `.keel/keel.toml`. This is a timestamp — the exact moment you initiated. There is no configuration to do. No dependencies to install. No API keys to set up.

**Question (do not answer yet):** What is this timestamp for?

---

### Practice 2: Feel the Field

```bash
keel status
```

You will see:
- Your vessel's name and birthday
- A heading (default: "discovery")
- 0 refits
- 5 agents listed (shipwright, lookout, engineer, purser, signalman)

Each agent has:
- A name and role
- A keel_date (same as yours — they were born when you initialized)
- A heading ("standby" — they haven't started yet)

**Observation:** The agents are not processes. They are not running. They are *archetypes* — descriptions of roles that could exist. The field shows potential, not activity.

**Question:** Why show agents that don't exist yet?

---

### Practice 3: Discover Your Constraints

```bash
keel probe
```

This reads your hardware. CPU cores, memory, disk, GPU if available. It does not set limits. It documents what is.

**Why this matters:** You cannot change the innate seaworthiness of your hardware. You can only learn it and work within it. The probe is the first act of learning your boat's physics.

**Practice:** Run `keel probe` on a different machine (a Raspberry Pi, a cloud VM, a laptop). Compare the outputs. Notice how the numbers shape what you can do.

---

### Practice 4: Prune What Isn't Your Boat

```bash
keel prune agents/signalman "Going solo — no multi-agent coordination needed"
```

The signalman is removed. The agents directory no longer contains it. But the *record* of the removal is preserved in `refits/refit-0001.json`.

```json
{
  "date": "2026-05-09T...",
  "component": "agents/signalman",
  "reason": "Going solo — no multi-agent coordination needed",
  "pruned": ["agents/signalman"]
}
```

**Why this matters:** The removal is documented with a reason. Future-you (or someone else) can read this record and understand *why* the signalman was pruned. The negative space is generative. It teaches.

**Practice:** Prune something else. Then `keel status` again. Notice the refit count incremented. The build record is accumulating.

---

### Practice 5: Refit Without Changing the Birthday

```bash
keel refit models/llm "Switched from Claude to DeepSeek"
```

A refit does not remove anything. It records a change with a reason. The `keel_date` in `.keel/keel.toml` does not change. The boat is still the same boat, even though the engine has been replaced.

**Question:** If every component can be replaced, what makes the boat the same boat?

**Practice:** Read `refits/refit-0002.json`. Notice it has no "pruned" field — only "component" and "reason". A refit is a change without removal. The distinction between prune and refit is the distinction between "this didn't belong" and "this was upgraded." Both are recorded. Both are generative.

---

### Practice 6: Run `keel status` Again

After a prune and a refit, the status shows:
- Refits: 2
- Agents: 4 (signalman is gone)
- Build record: 1 entry (the refits/ directory has 3 files: README + 2 records, but one is a prune)

**Observation:** The field has changed. Removing the signalman shifted the relationships between the remaining agents. The heading is still "discovery." The birthday is still the same. But the fleet is different.

**Practice:** Read through the full build record (`ls refits/`, `cat refits/*.json`). Each file tells a decision story. This IS the project memory. There is no changelog. There is no git log. There is only the build record.

---

### Practice 7: The Birthday and the Splash

```bash
keel launch --message "Splashing the fleet for first use"
```

This records a `splash.json` in the build record. The vessel is now "launched." Nothing functionally changes. But conceptually, the vessel has left the yard.

**Why this matters:** The distinction between "on the ways" (building/refitting) and "launched" (making way) is a distinction the developer makes for themselves. It orients future decisions. Everything before launch was preparation. Everything after is operation.

**Question:** What is the relationship between the `keel_date` and the `splash_date`?

---

### Understanding What You Just Did

You have now used all six Keel commands. Without anyone telling you, you have understood:

1. **First-person time** — the `keel_date` is your vessel's birthday, not an arbitrary install timestamp
2. **Tabula plena** — you started with 5 agents and pruned down, rather than starting with nothing and building up
3. **Negative space** — the pruned signalman is preserved in the build record with a reason. The removal is as informative as the presence
4. **Constraints breed clarity** — `keel probe` showed your hardware limits. You know what you're working with
5. **Refit is not restart** — the birthday didn't change when you changed the model
6. **The build record is the truth** — every decision, every prune, every refit is preserved with a reason

These are not facts you were taught. They are conclusions you reached through practice. Questions that arose during earlier practices (Why show agents that don't exist? What makes the boat the same boat? What is the timestamp for?) were answered by later practices not because the answers were given, but because the practice made the answers obvious.

**This is the methodology.** Not a framework to learn. A yard to inhabit. The architecture reveals itself through use.

---

### What You Can Do Next

The 5 TTL patterns (Tile, Task, Agent, Relationship, Trust) are not something you configure. They are something you *practice.*

**Practice 8:** Implement a Tile TTL in any language. One structure: `{ keel_date, ttl, data }`. One filter: `now < keel_date + ttl`. No GC. No sweep. The tile knows when to die.

**Practice 9:** Implement a bearing-rate collision detector. Two agents, each writing their heading to a shared file. A third observer reads both headings, computes the angular difference, tracks how it changes over time. If the difference isn't changing and the headings overlap, report a collision. No scheduler. No direct messages. The field is the communication channel.

**Practice 10:** Design a trust system where every assertion decays. No revocation. Only decay. Define your gray-zone thresholds. Use it for a week. Notice how the absence of hard cutoffs changes how you think about trust.

---

### Convincing a Skeptic

The skeptic's objection: "This is just TTL. TTL has existed for 40 years. What's new?"

The answer: TTL was the first instance. The contribution is recognizing that TTL, apoptosis, half-life, synaptic pruning, quorum sensing, market prices, and dropout are all the same architecture expressed in different materials. The unification is the insight. The Keel system is the demonstration.

But you don't need to convince anyone with words. The skeptic should run:

```bash
cargo install superinstance-keel
keel init skeptic-vessel
keel status
keel probe
keel prune
keel refit
keel launch
```

If the architecture is sound, practice will demonstrate it. If it is not, practice will reveal the flaw. In either case, the answer comes from doing, not from arguing.

---

*This document is part of the Keel canon. The full methodology is available at github.com/SuperInstance/keel.*

*"Know why you question, and the answer becomes less important on the big things."*
