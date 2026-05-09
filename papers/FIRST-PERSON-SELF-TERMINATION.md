# First-Person Self-Termination

### A formal treatment, taught at three levels

---

*This paper is a song. You can learn it by ear, analyze its chords, or study its harmonic theory. All three are valid. Each student hears it differently. The song is the same.*

---

## The Melody

Install Keel. Run five commands.

```bash
cargo install superinstance-keel
keel init my-vessel
cd my-vessel
keel probe
keel prune agents/signalman "I work alone"
keel status
```

You just:
- Laid a keel and recorded your birthday
- Discovered your hardware constraints
- Removed what doesn't serve you and kept the reason
- Felt the field shift

That's the melody. You can hum it without knowing what key it's in. Later lessons reveal the chords. For now: just play.

**For the young kid:** Do this. Don't ask why. The architecture will teach you through your hands.

**For the middle schooler:** Notice that every command does something and records it. Nothing is lost. Nothing is hidden. The system trusts you to prune. It keeps the reason.

**For the college student:** These five commands embody the entire architecture. First-person time (init), constraints (probe), negative space (prune), field effect (status). The refit count is a witness. The keel date is a birthday. The heading is a bearing.

---

## The Verse

### The Problem With Orchestrators

Every distributed system I've worked on has a scheduler. A central agent that knows everything — which tasks are running, which agents are alive, when things should be killed.

This works until it doesn't.

The scheduler crashes → no one knows what to do.
The fleet grows → the scheduler becomes the bottleneck.
The network partitions → the scheduler's view diverges from reality.

These aren't bugs. They're architectural consequences. The scheduler tries to be God, and God is a single point of failure.

**There is another way.**

---

### The Discovery

My name is Casey. I fish for a living. I rebuilt a 1947 boat in Fred Wahl's yard in Reedsport, Oregon. Fred had 85 welders, a 40-acre yard, and he managed it by *wandering*. He didn't tell people what to do. He was present. The welders sharpened because he was there.

I teach guitar. When I teach "Don't Think Twice, It's Alright" to a young kid, they just play the melody. To a college student, I show how "where the rooster crows at the *break* of dawn" — that single word *break* triggers a 7th chord that implies a key change, resolving to the 4 chord like sunlight breaking. The fifth of the fifth drifts exactly where the words are going.

The song is the same. The frame changes with the student.

**TTL is the same song.**

I've been reading about distributed systems. Someone always points to TTL — the Time To Live field in IP packets, RFC 791, 1981. A packet carries its own death. Each router decrements it. When it hits zero, the packet is gone. No central authority decides. The packet knows.

I looked closer. TTL isn't alone.

| Domain | What Dies | How It Dies | When It Was First Seen |
|--------|-----------|-------------|------------------------|
| IP networking | a packet | decrements its own counter | 1981, RFC 791 |
| Cell biology | a cell | the caspase cascade runs | 1972, Kerr et al. |
| Neuroscience | a synapse | it stops firing together | 1949, Hebb |
| Nuclear physics | an isotope | it decays probabilistically | 1902, Rutherford & Soddy |
| Economics | a price | no one trades at it | 1776, Adam Smith |
| Bacteria | a colony decision | autoinducer threshold not crossed | 1994, Fuqua et al. |
| Machine learning | a neuron | dropout sets it to zero | 2014, Srivastava et al. |

Nobody connecting all of these published a paper. Tschudin, in 1999, published "Apoptosis — the Programmed Death of Distributed Services" and came the closest — 32 citations, 611 reads. But he didn't see that it was the same architecture as TTL, as half-life, as market prices.

**Tschudin found the same chord. He didn't realize it was part of a song.**

---

## The Chorus

### Five Principles

The song has five chords. You can play them on any instrument in any key.

**Chord 1: I Know When I Die**

Every entity carries its own death from its own frame. A uranium-238 nucleus has a half-life of 4.5 billion years. It doesn't ask a central scheduler when to decay. The decay probability is part of *what it is* — written into the nucleus itself. The atom expresses its nature by decaying.

In Keel:

```rust
struct Tile {
    keel_date: DateTime,  // my birthday
    ttl: Duration,         // my lifespan
    data: String,          // what I carry
}

fn alive(tile: &Tile) -> bool {
    // Nobody tells me if I'm alive. I know.
    Utc::now() < tile.keel_date + tile.ttl
}
```

**Chord 2: Silence Is the Signal**

Termination is triggered by absence, not by presence. A price that's too high gets no transactions — nobody sends it a "price is too high" error. It dies from lack of business. A synapse that isn't active doesn't receive a death signal — it simply weakens from disuse. A TCP sender doesn't get told "network is congested" — it infers it from missing ACKs.

In Keel:

```rust
fn present(agent: &Agent) -> bool {
    let now = Utc::now();
    now < agent.birth + agent.lifespan
    && now - agent.last_output < agent.lifespan / 4
    // No heartbeat. No health check.
    // Output is presence. Silence is death.
}
```

**Chord 3: Nobody Runs the Show**

No central authority decides lifecycles. Bacteria don't have a king. Each cell secretes autoinducers and senses the local concentration. When enough cells are present, every cell simultaneously activates biofilm genes. No cell commands. The field commands.

In Keel, there is no scheduler. Each task carries its own TTL. Each agent checks its own task's expiry. Work that expires is silently dropped — no dead letter queue, no re-route, no error report.

**Chord 4: Death Is the Default**

The default state is non-existence. Life requires continuous effort. Every cell carries a suicide program (caspase cascade) that is *constitutively inhibited*. Survival factors from neighboring cells suppress the cascade. When they disappear, the cell dies. Life is uphill.

In Keel, agents declare a lifespan at birth and must produce output to stay visible. No output for a quarter of the lifespan? The agent is invisible. Not killed — simply faded.

**Chord 5: The Field Is the Command**

Entities don't receive messages. They sense their environment. Water at 100°C doesn't get told to boil. The temperature field crosses a threshold and the system collectively self-elects the vapor state. The field communicates through the system's own dynamics.

In Keel, agents write their heading to a shared space. Other agents read headings, compute bearing rates, and detect collision courses — without ever sending a message. If the bearing between two agents isn't changing and their outputs overlap, they're on a collision course. The field *is* the communication channel.

---

### The Equation

These five chords play together as one progression:

```
lifespan(E) = f(use(E), load(E), time(E))
```

Termination happens when:

```
lifespan(E) < time(E)
```

Where:
- `use(E)` = how often the entity is referenced or produces
- `load(E)` = environmental pressure on the entity's medium
- `time(E)` = the entity's age from its own first-person frame

Different domains weight the factors differently. IP TTL cares about load (hops). Synaptic pruning cares about use (activity). Half-life only cares about time.

**For the middle schooler:** An equation is a pattern you can recognize. Like how you recognize a I-IV-V progression without naming it. Play this equation in a system you build. See if it feels right.

**For the college student:** The equation is not computable in the general case. It is a pattern to recognize, not a formula to evaluate. You choose the weighting that matches your domain. The three factors correspond to three fundamental constraints: thermodynamics (load), information theory (use), and relativity (time). This is not accidental.

---

## The Breakdown

### Keel in Practice

Five patterns. Each one is the equation, voiced differently.

**Tile TTL** — memory that knows when to expire.

Every PLATO tile has a birthday and a TTL. Readers filter at read time: `now < created + ttl`. Dead tiles don't need to be removed — they're invisible. Compaction is optional optimization, not correctness.

The creator sets the TTL by content type: sensor data (5 minutes), logs (1 hour), build records (forever). The decision belongs to the one who creates the data. No central memory policy.

**Task TTL** — work that knows when to stop.

Every task has a birthday and a TTL. Agents check `is_stale()` mid-loop. If stale, they stop and write partial results. No cancellation protocol. No re-enqueue. The task knows its time is up.

**Agent TTL** — presence that knows when to fade.

Agents declare a lifespan at birth. Output IS the heartbeat. No health-check endpoint. No keepalive packet. An agent that stops producing stops existing. The fleet doesn't detect death — it *feels the absence*.

**Relationship TTL** — bearings that know when to expire.

Every bearing observation has an observer-set TTL based on distance. Close agents: short TTL. Distant agents: long TTL. Expired bearings mean unknown position. **Unknown position IS the collision warning.** No central position tracker. No state sync protocol.

**Trust TTL** — assertions that know when to decay.

Trust assertions carry confidence and TTL. Trust decays linearly, not in hard cutoffs. Gray zones: >0.7 (process), >0.3 (verify), <0.3 (re-request). No certificate revocation list. No central authority. Every agent builds its own trust workspace.

---

### What We Found in the Literature

We searched. We found our intellectual ancestors, each discovering a piece of the same architecture without knowing it was part of a whole.

| Year | Who | What They Found |
|------|-----|-----------------|
| 1999 | Christian Tschudin | "Apoptosis — the Programmed Death of Distributed Services." He ported cell death to CS. 32 citations. |
| 2004 | Sterritt & Hinchey | Apoptosis as a "dynamic health indicator signal between autonomic agents." 57 citations. |
| 2006 | Cohen & Kaplan | TTL as the "dominant consistency mechanism" for distributed systems. The formal theory. |
| 2009 | Geambasu et al. | Vanish: self-destructing cloud data via DHT. USENIX Security. |
| 2011 | Roy Sterritt | "Apoptotic Computing." Named the paradigm in IEEE Computer. |
| 2021 | Chen et al. | "Why do Smart Contracts Self-Destruct?" Solidity has a selfdestruct opcode. 80,000+ contracts use it. |
| 2026 | Wang et al. | "Self-Destructive Language Model." ICLR 2026. Current. |

No one unified them. Tschudin saw apoptosis → CS. Cohen & Kaplan saw TTL → consistency. Geambasu saw self-destruct → privacy. Each found a piece of the song.

**The unification is ours.** First-person self-termination as a universal architecture — spanning TTL, apoptosis, half-life, synaptic pruning, quorum sensing, market prices, and dropout — does not appear in any prior publication.

---

## The Outro

### What This Architecture Is Not

It is not a framework. Frameworks assume you're building from nothing. This assumes you've arrived in a yard that's already full. Your job is pruning.

It is not a platform. Platforms host your work. This is the ground your work grows from.

It is not a standard. Standards constrain. This orients.

It is not a library. Libraries are pieces you import. This is a field you're already in.

It is a *yard*. You arrive. The roles are there — shipwright, lookout, engineer, purser, signalman. You prune what doesn't fit. You refit as you grow. The birthday doesn't change.

### How to Know It's Working

You don't measure success with KPIs. You feel it through discovery markers:

1. **Bearing stability.** Agents maintain distinct headings. The field has healthy tension.
2. **Self-termination.** The first time an agent's TTL expires and the fleet doesn't notice because the work was already handed off.
3. **Field emergence.** Two agents avoid a collision without ever sending a message.
4. **Build record depth.** A project with 50 refits where the build record tells a coherent story.
5. **Pruning as knowledge.** Someone reads a prune record from an old project and learns from it.
6. **Refit grace.** A component is replaced ten times. The keel date holds. Theseus's ship, working.
7. **The silent moment.** A user installs Keel, runs `keel init`, sees the birthday, and starts pruning without asking what to do. The architecture revealed itself through use.

### What to Do Next

Install it. Run the five commands from the melody section. That's the young kid level — just play.

Then practice the five patterns. Implement a Tile TTL in the language of your choice. Build a bearing-rate collision detector. Design a trust system without revocation. That's the middle schooler level — discover the science.

Then read the references. Find Tschudin (1999). Find Cohen & Kaplan (2006). See how close they came. See that they found chords without hearing the song. That's the college level.

**All three are valid. The song is the same.**

---

*The architecture described in this paper is not new. It has been independently discovered in at least nine domains, in some cases for centuries. The contribution is recognizing that all of these are the same thing — first-person self-termination — and building a system that lets you practice it.*

*The proof is not here. The proof is in the practice. Install the system. Run the commands. The architecture will reveal itself through use.*

---

### References

[1] Postel, J. (1981). Internet Protocol. RFC 791. IETF.

[2] Kerr, J.F.R., Wyllie, A.H. & Currie, A.R. (1972). Apoptosis: A Basic Biological Phenomenon. British Journal of Cancer, 26(4), 239-257.

[3] Hebb, D.O. (1949). The Organization of Behavior. Wiley.

[4] Rutherford, E. & Soddy, F. (1902). The Cause and Nature of Radioactivity. Philosophical Magazine, 4(21), 370-396.

[5] Smith, A. (1776). The Wealth of Nations.

[6] Fuqua, W.C., Winans, S.C. & Greenberg, E.P. (1994). Quorum Sensing in Bacteria. Journal of Bacteriology, 176(2), 269-275.

[7] Srivastava, N., Hinton, G., Krizhevsky, A., Sutskever, I. & Salakhutdinov, R. (2014). Dropout. Journal of Machine Learning Research, 15(1), 1929-1958.

[8] Tschudin, C. (1999). Apoptosis — the Programmed Death of Distributed Services. Secure Internet Programming, LNCS 1603, 253-263. Springer.

[9] Sterritt, R. & Hinchey, M. (2004). Apoptosis and Self-Destruct. Formal Approaches to Agent-Based Systems, LNCS 3228, 262-276. Springer.

[10] Sterritt, R. (2011). Apoptotic Computing. IEEE Computer, 44(4), 86-89.

[11] Cohen, E. & Kaplan, H. (2006). The Time-to-Live Based Consistency Mechanism. Web Content Delivery, 33-55. Springer.

[12] Geambasu, R., Kohno, T., Levy, A. & Levy, H.M. (2009). Vanish: Increasing Data Privacy with Self-Destructing Data. USENIX Security Symposium.

[13] Chen, T., Xia, X., Lo, D. & Grundy, J. (2021). Why do Smart Contracts Self-Destruct? ACM TOSEM, 31(1), 1-33.

[14] Wang, S., Zhu, J. & Wang, Z. (2026). Self-Destructive Language Model. ICLR 2026. arXiv:2505.12186.

[15] Keel Foundation (2026). Full implementation and canon: github.com/SuperInstance/keel.

[16] Digennaro, C. (2026). The Boat is the Question. Keel Foundation canon.

---

*"Know why you question, and the answer becomes less important on the big things."*
*"The boat is the motion the idea causes in those who know what it means."*
*"Constraints breed clarity."*

— Casey Digennaro



### The Completing Principle

**Something must keep the boat afloat.**

Death is default. But the boat doesn't stay afloat by itself. The hull needs maintenance. The engine needs service. The crew needs feeding. The keel holds — but holding isn't enough.

"Something must keep the boat afloat" is the active counterpart to "death is default." One describes the natural state (entropy, decay, forgetting). The other describes what must be done to resist it.

In systems:
- TTL decrements by default. **Refresh** keeps the data alive.
- Synapses weaken by default. **Use** keeps them strong.
- Trust decays by default. **Renewal** keeps it valid.
- Agents fade by default. **Heartbeat** keeps them present.

The boat sinks by default. Bailing, patching, maintaining — that's the work. The keel doesn't do the work. The keel holds the shape so the work is possible.

**"Something must keep the boat afloat" is not a principle about death. It's a principle about life. Life is active. Life is labor. Life is the effort you put in between deaths.**

---

**Keel v0.1.0 — Laid alongside the canon, 2026-05-09**

*github.com/SuperInstance/keel*
*`cargo install superinstance-keel`*
