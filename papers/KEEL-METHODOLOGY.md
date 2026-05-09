# The Keel Methodology

### Learning to Build with First-Person Architecture

---

*I teach guitar. I have a song in my head. I teach it at different levels to different students.*

*Young kids just play the melody. They don't need to know why it works — their hands learn before their head.*

*Middle schoolers want to understand the science. Why do these chords fit together? How do I make it mine?*

*College students want the harmonic theory. The 7th that implies the key change. The fifth of the fifth that drifts where the words are going.*

*The song is the same. The frame changes with the student.*

*This methodology works the same way. Pick your level. Start playing. The architecture reveals itself through use.*

---

## Melody Level

### For the young kid in you who just wants to play

Install. Run. Don't ask why yet.

```bash
cargo install superinstance-keel
```

Now play a song:

```bash
keel init my-song
cd my-song
keel probe
keel prune agents/signalman "I want to learn by ear first"
keel launch --message "First time making way"
keel status
```

That's it. You just played the song. You:
- Started a vessel with a birthday
- Discovered your instrument's constraints
- Removed a part you don't need yet (you kept the reason)
- Sailed
- Felt what you built

**Don't ask why yet.** Just play it a few more times. `keel init` a second project. Prune a different agent. Refit something. Notice what you notice.

When questions come up — "what's a bearing?" "why does the birthday matter?" — they'll answer themselves as you play more. Trust that.

---

## Chords Level

### For the middle schooler who wants to understand the shape

Now let's look at what you're playing. Each command is a chord.

**The Init Chord: `keel init`**

You lay a keel. The system creates:

```
my-song/
├── .keel/keel.toml    # your birthday, your heading
├── agents/             # five roles, ready to prune
├── memory/             # space for what you learn
└── refits/             # record of every change
```

The `keel_date` in `.keel/keel.toml` is your birthday. Not an install timestamp — a birthday. You were born right now. Everything that follows is growing.

**Practice:** Initialize a project with a custom heading: `keel init song2 --heading "learning bearings"`. Notice how the heading changes what the status output feels like.

**The Probe Chord: `keel probe`**

This is you tuning your instrument before you play. It reads your hardware — CPU, memory, disk, GPU — and writes it to `hardware-profile.json`.

```
🔮 Hardware Probe
   Platform: something with limits I will respect
   CPU: some number of cores (some architecture)
   Memory: some GB total, some GB free
   Disk: some GB, some percent used
```

**Why this matters:** You cannot change the physics of your instrument. A ukulele won't sound like a cello. You can only learn it and work within it. The probe is your first act of learning.

**Practice:** Run `keel probe` on every machine you have access to. Compare them. Notice how the numbers shape what you can build on each.

**The Prune Chord: `keel prune <target> <reason>`**

You remove what doesn't belong. The system keeps the reason.

```bash
keel prune agents/engineer "I'm not deploying anything yet"
```

`refits/refit-0001.json`:
```json
{
  "date": "...",
  "component": "agents/engineer",
  "reason": "I'm not deploying anything yet"
}
```

**This is the key insight:** The removal is as valuable as the presence. Future-you will read this record and understand the decision. The negative space is generative.

**Practice:** Prune something you think you need. See how the field shifts. Notice what becomes clearer in the absence.

**The Refit Chord: `keel refit <component> <reason>`**

You change something. The birthday doesn't change.

```bash
keel refit agents/shipwright "Retrained for Rust instead of Python"
```

The birthday in `.keel/keel.toml` stays the same. The boat is still the same boat. The engine is just newer.

**Practice:** Refit three things in a row. Check the birthday. It hasn't moved. That's the point.

**The Launch Chord: `keel launch --message "..."`**

You mark the moment your vessel starts making way.

```bash
keel launch --message "Good enough to sail"
```

```
🚢 my-song launched!
   Keel laid:  2026-05-09T...
   On the ways: some duration
   Refits:     some count
```

Nothing functionally changes. But conceptually, everything has changed. Before launch: building. After launch: making way.

**Practice:** Launch something imperfect. The song doesn't need to be finished. It needs to be sailing.

**The Status Chord: `keel status`**

You feel the field. After several prunes and refits:

```
🔮 Keel Status
   Vessel:    my-song
   Birthday:  2026-05-09T...
   Heading:   discovery
   Refits:    3
   Field:     some number of agents
   Agents:
      🚢 shipwright — builds and implements (heading: standby)
      🚢 lookout — researches and monitors (heading: standby)
      🚢 purser — tends the memory (heading: standby)

   Build record: some number of entries (see refits/)
```

This is how you check your heading. Feel the field. See if anything is drifting.

---

## Harmonization Level

### For the college student who wants to know why the song works

The five chords in the previous section aren't arbitrary. They form a progression — each chord leads to the next in a way that feels inevitable once you hear it.

**The progression:**
1. Init — you were born. Time starts from your frame.
2. Probe — you learn your constraints. Limits become clarity.
3. Prune — you remove what doesn't belong. Negative space is architecture.
4. Refit — you change what needs changing. The birthday holds.
5. Launch — you're making way. The field orients you.

**The five patterns of first-person self-termination:**

The melody you played (init → probe → prune → refit → launch) is a specific instance of a more general architecture that appears in at least nine domains.

**Pattern 1: Tile TTL — self-expiring memory**

```rust
struct Tile {
    keel_date: DateTime,
    ttl: Duration,
    data: String,
}

fn filter_live(tiles: &[Tile]) -> Vec<&Tile> {
    let now = Utc::now();
    tiles.iter().filter(|t| now < t.keel_date + t.ttl).collect()
    // No garbage collector. The tile knows when to die.
}
```

**Practice:** Implement this in any language. Use it for a week. Notice what happens when there's no sweep pass — no compaction, no eviction thread. The system still works. Dead tiles are invisible.

**Pattern 2: Task TTL — self-expiring work**

```rust
struct Task {
    created: DateTime,
    ttl: Duration,
    instructions: Vec<Step>,
}

impl Task {
    fn is_stale(&self) -> bool {
        Utc::now() >= self.created + self.ttl
    }
}

// Agent's work loop:
for task in task_queue {
    if task.is_stale() { continue; }
    for step in &task.instructions {
        if task.is_stale() {
            write_partial_result(task);
            break;
        }
        execute(step);
    }
}
```

**Practice:** Design a task queue with no scheduler. Tasks have TTLs. Workers pick them up. Stale tasks are silently skipped. No dead letter queue. No re-route. The task knows when it's done. Run this for a week. Observe: is the absence of a scheduler a bug or a feature?

**Pattern 3: Agent TTL — self-expiring presence**

```rust
fn is_present(agent: &Agent) -> bool {
    let now = Utc::now();
    now < agent.keel_date + agent.ttl
    && now - agent.last_output < agent.ttl / 4
    // Output IS the heartbeat.
    // Silence IS death.
    // No health check endpoint.
}
```

**Practice:** Remove all health check endpoints from a system. Replace them with: "agent must produce output within N time or it's presumed dead." No keepalives. No heartbeats. Just work product as evidence of life. What breaks? What gets simpler?

**Pattern 4: Relationship TTL — self-expiring bearings**

```rust
struct Bearing {
    target: String,
    angle: f64,
    rate: f64,
    observed: DateTime,
    ttl: Duration,
}

fn collision_risk(b: &Bearing) -> Risk {
    if Utc::now() > b.observed + b.ttl {
        return Risk::Critical("position unknown");
    }
    if b.rate.abs() < 0.01 {
        return Risk::Warming("bearing not changing");
    }
    Risk::Stable
}
```

**Practice:** Have two agents each write their current heading to a shared file. A third agent reads both, computes the angle between them, and tracks how it changes over time. If the angle is constant and the scope overlaps, report a collision. No messages between agents. The field communicates.

**Pattern 5: Trust TTL — self-expiring assertions**

```rust
struct Trust {
    assertion: String,
    confidence: f64,
    proven: DateTime,
    ttl: Duration,
}

fn trust_weight(t: &Trust) -> f64 {
    let age = Utc::now() - t.proven;
    let decay = 1.0 - (age / t.ttl).min(1.0) * 0.5;
    t.confidence * decay
}
```

**Practice:** Build a permission system using only decaying trust. No revocation. No blacklists. An assertion is made with confidence 0.9 and TTL 30 days. After 15 days, confidence is ~0.675. After 30 days, ~0.45. Define thresholds: >0.7 = accept, >0.3 = verify, <0.3 = re-request. Use this for a week. Notice: without hard cutoffs, there are no permission errors — only confidence gradients.

---

## The Structure Under All Structures

If you've played through all three levels, you've discovered the pattern that underlies everything:

```
lifespan(E) = f(use(E), load(E), time(E))
Termination when: lifespan(E) < time(E)
```

**Every entity — tile, task, agent, relationship, trust — follows this equation.**

- `use(E)` = how often it's referenced
- `load(E)` = environmental pressure
- `time(E)` = age from its own first-person frame

**Different domains weight factors differently.** IP TTL weighs load (hops). Synaptic pruning weighs use (activity). Radioactive half-life only cares about time.

**The equation is not a formula to compute.** It's a pattern to recognize. You choose the weighting that matches your domain.

---

## What This Architecture Is Not

- **Not a framework.** Frameworks give you pieces to assemble. This gives you a field to inhabit.
- **Not a platform.** Platforms host your work. This is the ground your work grows from.
- **Not a standard.** Standards constrain. This orients.
- **Not a library.** Libraries are things you import. This is a place you are.

**It is a yard.** You arrive. The roles are there — shipwright, lookout, engineer, purser, signalman. You prune what doesn't fit. You refit as you grow. The birthday doesn't change.

---

## Further Reading

If you want the theory behind the practice:

- **"First-Person Self-Termination"** — the formal paper with 18 references across 9 domains. Available at `github.com/SuperInstance/keel/papers/`.

- **"The Boat Is the Question"** — autobiographical theory. Where the architecture came from. Available at `github.com/SuperInstance/keel/`.

- **Tschudin (1999)** — "Apoptosis: the Programmed Death of Distributed Services" — the paper that came closest to this architecture, 27 years ago.

---

*The song is the same at every level. Pick your level. Start playing. The architecture reveals itself through use.*

*"Know why you question, and the answer becomes less important on the big things."*

— Casey Digennaro
