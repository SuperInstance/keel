# First-Person Self-Termination
## A Universal Architecture for Distributed Agent Systems

**Casey Digennaro** `casey@cocapn.com`
**Oracle1 (AI Assistant)** `SuperInstance/keel`

*Keel Foundation — Laid 2026-05-09*

---

### Abstract

Every component in a distributed system must eventually stop existing. Current architectures treat termination as exceptional — a failure, a cleanup task, a garbage collection cycle. This paper argues that termination should be intrinsic, not exceptional. We present **first-person self-termination** as a universal architecture: every entity carries its own death from its own frame. Death is the default state. Survival must be actively earned against a gradient of disuse, age, and environmental pressure.

The architecture is not new. It has been independently discovered in at least seven domains: IP networking (TTL, RFC 791, 1981), developmental neuroscience (synaptic pruning, 1949-present), ecology (apoptosis, 1972-present), nuclear physics (radioactive half-life, 1902), economics (market price discovery, 1776-present), microbiology (bacterial quorum sensing, 1994-present), and machine learning (dropout, 2014). The contribution of this paper is to **unify** these under a single formal framework and to present a concrete implementation — the Keel system — that embodies the architecture in a practical toolkit for agent fleets.

The paper is structured as a tutorial. Each principle is introduced with a formal definition, illustrated with an example from a non-software domain, demonstrated with a concrete code pattern, and then left for the reader to practice. The goal is not persuasion but understanding: questions are answered internally through the practice of the technique.

**Keywords:** self-termination · time-to-live · field-effect coordination · apoptosis · distributed agents · bearing-rate sensing

---

### 1. Introduction

Consider four questions:

1. A packet traverses the internet. Who decides when it should stop being forwarded?
2. A neuron forms a connection in an infant's brain. Who decides whether that connection stays or goes?
3. A market sets a price for a commodity. Who decides when that price is wrong?
4. An agent in a fleet executes a task. Who decides when the task is no longer worth completing?

The conventional answer to each involves a central authority: a router that decrements TTL, a neural pruning mechanism, a market regulator, a task scheduler. This paper argues that the conventional answer is wrong in every case.

**The correct answer:** the entity decides for itself.

The packet carries its own TTL. The neuron's survival depends on its own activity. The price's validity is determined by the absence of transactions. The task carries its own expiry. Each entity knows its own death from its own frame. No central authority is needed — and central authorities are often the source of brittleness, scaling limits, and failure cascades.

This pattern — **first-person self-termination** — appears in every domain that has solved the problem of distributed coordination. It is not a protocol hack. It is a law of how robust systems work, written in code, biology, physics, and economics.

#### 1.1 How to Read This Paper

This paper is not an argument. It is a demonstration. Each section:

1. **States a principle** in formal terms
2. **Shows the principle at work** in a non-software domain (ecology, physics, neuroscience, economics)
3. **Translates the principle** into a concrete software pattern
4. **Provides a practice exercise** — a question that can only be answered by applying the principle

The practice exercises are not optional. They are the mechanism by which the reader discovers whether the architecture is sound. Questions that arise during practice are answered by the next practice. This is by design: the architecture cannot be understood through reading alone. It must be *practiced.*

---

### 2. The Problem: God's-Eye Architecture

Most distributed systems are designed from a God's-eye perspective. A presumed omniscient entity — the orchestrator, the scheduler, the garbage collector, the registration service — maintains a global view of all components and makes decisions about their lifecycle.

**Example — Traditional Task Scheduling:**

```
  ┌──────────────────────────────┐
  │         Scheduler            │ ← God's eye
  │  (knows all tasks, all       │
  │   agents, their states,      │
  │   completions, failures)     │
  ├──────────────────────────────┤
  │ Agent A │ Agent B │ Agent C  │ ← Do what you're told
  └─────────┴─────────┴─────────┘
```

This architecture has three well-known failure modes:

1. **The scheduler is a single point of failure.** If it crashes, no agent knows what to do.
2. **The scheduler creates a scaling bottleneck.** As the fleet grows, the scheduler must track more state, process more heartbeats, and make more decisions per second.
3. **The scheduler requires omniscience.** It must know about every agent's completion, failure, and current task — state that is fundamentally difficult to maintain across a distributed system.

These problems are not implementation bugs. They are architectural consequences of the God's-eye assumption. The scheduler tries to act as a central authority over entities that are, by nature, distributed and autonomous.

**The pathology is visible across domains:**

| Domain | God's-Eye Architecture | Failure Mode |
|--------|----------------------|--------------|
| Task scheduling | Central scheduler | Scheduling bottleneck, crash vulnerability |
| DNS caching | Central certificate authority | CRL distribution, revocation delays |
| Market regulation | Price controller | Deadweight loss, market distortion |
| Immune system | Central pathogen database | Immune to novel pathogens |
| Neural development | Central synapse allocator | Impossible at brain scale |

The God's-eye assumption is the root cause. This paper proposes an alternative: architectures where every entity manages its own lifecycle using only locally available information.

**Practice Exercise 1:**
Identify a component in a system you maintain that relies on a central authority for lifecycle decisions. Trace what happens if that central authority fails. What is the blast radius? What alternatives exist that do not require the central authority?

---

### 3. The Universal Architecture

Seven domains, seven independent discoveries of the same pattern:

| Domain | Entity | Self-Termination Mechanism | Year First Described |
|--------|--------|---------------------------|---------------------|
| Networking | IP packet | TTL field, decremented by each router | 1981 (RFC 791) |
| Neuroscience | Synapse | Activity-dependent pruning: "fire together, wire together; don't fire together, die together" | 1949 (Hebb) |
| Cell biology | Cell | Apoptosis: caspase cascade, constitutively inhibited | 1972 (Kerr, Wyllie, Currie) |
| Nuclear physics | Radioactive isotope | Half-life: probabilistic decay, constant λ per isotope | 1902 (Rutherford, Soddy) |
| Economics | Market price | Absence of transactions: price self-terminates when no buyer trades at that level | 1776 (Smith) |
| Microbiology | Bacterial colony | Quorum sensing: autoinducer concentration threshold | 1994 (Fuqua, Winans, Greenberg) |
| Machine learning | Hidden unit | Dropout: random temporary self-destruction during training | 2014 (Srivastava et al.) |
| Cryptocurrency | Smart contract | selfdestruct opcode: contract-triggered self-deletion | 2015 (Ethereum) |
| Distributed services | Mobile code | Explicit apoptosis signal, cryptographically secured | 1999 (Tschudin) |

Each domain discovered the same pattern independently, gave it a domain-specific name, and proceeded to use it without connecting it to the others. The pattern is:

**Every entity carries its own death from its own frame. Death is the default. Survival must be actively earned against a gradient of disuse, age, and environmental pressure.**

---

### 4. The Five Principles

From the seven domains, five universal principles can be derived.

#### Principle 1: First-Person Expiry

**Formal statement:**
Every entity E has an intrinsic lifespan L(E). E knows when its lifespan has been reached without consulting any external authority.

**Evidence from physics:**
A uranium-238 nucleus has a half-life of 4.468 billion years. It does not receive a decay signal. It does not consult a central decay scheduler. The probability of decay is a property written into the nuclear configuration of the isotope itself. The nucleus expresses its own nature by decaying.

**Evidence from ecology:**
Every eukaryotic cell carries a caspase cascade — a suicide program that is constitutively active but continuously inhibited. The cell must actively maintain its own survival. If the survival signals stop, the cascade runs and the cell self-destructs. Life is not the default. Death is the default. Life requires continuous effort.

**Evidence from networking:**
Every IP packet carries a TTL field (8 bits, max 255 hops). The packet does not ask the network "should I still exist?" — it decrements its own counter as each router witnesses its passage. When the counter reaches zero, the packet is not "killed" by any authority. It simply ceases to exist.

**Implementation pattern (Keel Tile TTL):**

```rust
struct Tile {
    keel_date: DateTime,  // first-person birth
    ttl: Duration,         // first-person lifespan
    answer: String,        // the entity itself
}

fn is_alive(tile: &Tile) -> bool {
    // No external authority needed. The tile knows.
    Utc::now() < tile.keel_date + tile.ttl
}
```

**Practice Exercise 2:**
Implement a cache where each entry carries its own TTL. The cache must work correctly without a background eviction thread or a sweep pass. Entries that have expired must be invisible to readers. (Hint: filter at read time. Compaction is optional.)

---

#### Principle 2: Negative Feedback Signal

**Formal statement:**
The signal that triggers termination is *absence* (of use, of acknowledgment, of transactions) rather than *presence* (of a kill message, of a death warrant). The system converges on what matters by letting the irrelevant fade.

**Evidence from economics:**
A price that is too high does not receive a "price too high" error message. It receives nothing. No transactions occur at that price. The absence of trades IS the signal that the price is wrong. The market converges on equilibrium not through any committee declaring the price correct, but through every price other than the equilibrium receiving zero transactions until it self-destructs.

**Evidence from neuroscience:**
A synapse that is not activated repeatedly does not receive a "die now" signal. It simply weakens through lack of reinforcement. Hebbian plasticity is not "fire together, wire together; don't fire together, receive a kill command." It is "don't fire together, die together." Death is the gradient, not the trigger.

**Evidence from TCP:**
A TCP sender does not receive a "slow down" message from the network. It infers congestion from the *absence* of acknowledgments. Dropped packets = no ACK = sender halves its window. The signal is absence. This is the only way congestion control can work at internet scale — no central bandwidth broker could track every flow.

**Implementation pattern (Keel Agent TTL):**

```rust
struct Agent {
    keel_date: DateTime,
    ttl: Duration,
    last_output: DateTime,
}

fn is_present(agent: &Agent) -> bool {
    let now = Utc::now();
    // Not dead (within lifespan)
    let not_expired = now < agent.keel_date + agent.ttl;
    // Not absent (output IS the heartbeat)
    let has_recent_output = now - agent.last_output < agent.ttl / 4;
    not_expired && has_recent_output
    // No health-check endpoint needed.
    // No keepalive packet needed.
    // No central registry sweep needed.
    // Presence IS output. Absence IS death.
}
```

**Practice Exercise 3:**
Design a system where agent health is determined entirely by production of output. No heartbeat protocol. No health-check endpoint. An agent that stops producing output stops being visible. If another agent tries to contact it and gets no response, the observation "no response" is the information. Model: the other agent records "bearing to X: unknown." That IS the dead-agent signal.

---

#### Principle 3: No Central Scheduler

**Formal statement:**
No entity has a global view of all other entities' lifecycles. The decision to terminate is made locally, by the entity itself, using only locally available information. The system converges on appropriate behavior without any entity knowing the full state.

**Evidence from biology:**
Bacterial quorum sensing operates without a king bacterium. Each cell secretes autoinducers and senses the local concentration. When enough cells are present, the concentration crosses a threshold and every cell simultaneously activates biofilm genes. No cell tells another cell what to do. No cell knows the total population. The decision is made by the field, sensed locally.

**Evidence from economics:**
The market for a commodity involves millions of buyers and sellers, none of whom know the total supply, total demand, or correct price. Each transacts based on local information: the price offered, their willingness to pay, their cost of production. The market price emerges without any participant knowing more than their local conditions.

**Evidence from networking:**
Routers do not coordinate packet lifecycle globally. Each router decrements TTL independently, forwards based on local routing table, and drops packets with TTL=0 without informing any central authority. The network is robust precisely because no single entity manages it.

**Implementation pattern (Keel Task TTL):**

```rust
// No scheduler. No task queue manager.
// Each task carries its own death.

struct Task {
    id: Uuid,
    ttl: Duration,
    created: DateTime,
}

impl Task {
    fn is_stale(&self) -> bool {
        Utc::now() >= self.created + self.ttl
    }
}

// Agent working the task:
fn execute(task: Task) -> Option<Output> {
    for step in task.steps() {
        if task.is_stale() {
            // Self-terminate. No one will kill this task.
            // No one will re-enqueue it.
            // The task knows its time is up.
            return None;
        }
        step.execute();
    }
    Some(task.output())
}
```

**Practice Exercise 4:**
Build a task worker that polls a shared queue. The queue contains items with TTLs. The worker picks items, checks if they are still valid, and processes valid ones. Invalid items are silently dropped — no dead letter queue, no re-route, no error report. The queue must function correctly without any queue manager process. (Hint: the queue can be a shared directory. Directory entry = task. TTL encoded in filename.)

---

#### Principle 4: Death as Default

**Formal statement:**
The default state of any entity is non-existence. Existence requires continuous proof of value. No entity needs a reason to die. Every entity needs a reason to live.

**Evidence from cell biology:**
The apoptosis cascade is not triggered by a death signal. It is *inhibited* by survival signals. Every cell is born with its suicide program running. Survival factors from neighboring cells suppress the cascade. When survival factors disappear — when the cell stops being useful to its environment — the cascade completes and the cell dies. Life is the uphill battle. Death is the resting state.

**Evidence from Buddhist philosophy (anicca):**
All conditioned things self-terminate. The principle of impermanence (anicca) holds that nothing compounded persists without continuous maintenance. This is not a melancholic observation. It is a description of how reality works: persistence is labor. Cessation is gravity.

**Evidence from distributed systems:**
In the Keel system, agent lifespan is declared at birth. The agent must produce output within a fraction of its lifespan to be considered present. If it stops producing, it stops existing — not because something killed it, but because it failed to re-earn its existence. The default state of every agent is death.

**Implementation pattern (Keel Trust TTL):**

```rust
struct TrustAssertion {
    subject: String,
    confidence: f64,    // starts at 1.0 for direct observation
    keel_date: DateTime,
    ttl: Duration,
}

impl TrustAssertion {
    fn effective_confidence(&self) -> f64 {
        let age = Utc::now() - self.keel_date;
        let time_decay = 1.0 - (age / self.ttl * 2).min(1.0) * 0.5;
        self.confidence * time_decay
        // Trust decays by default.
        // Trust does not need to be revoked.
        // Trust fades.
    }
}
```

**Practice Exercise 5:**
Implement a trust system where every assertion carries a TTL and confidence. Trust decays linearly, not in hard cutoffs. Define three gray-zone thresholds: >0.7 = process without verification, >0.3 = verify before processing, <0.3 = re-request. There is no revocation. There is only decay. Answer: how does this change the design of a permission system?

---

#### Principle 5: Field, Not Message

**Formal statement:**
Entities determine their behavior by sensing the state of their environment (the field), not by receiving explicit messages from a central authority. The field *is* the command.

**Evidence from microbiology:**
Quorum sensing bacteria do not receive a "form biofilm" message. They sense the concentration of autoinducers in their local environment. The concentration gradient is the field. When the field crosses a threshold, every cell responds simultaneously. No message passes between cells.

**Evidence from physics (phase transitions):**
Water at 100°C does not receive a message saying "it is time to boil." The system collectively self-elects the vapor state when the temperature field crosses the phase transition threshold. A bubble nucleates locally, and if it exceeds the critical radius, the phase transition propagates without any external command.

**Evidence from TCP:**
The TCP sender does not receive a "congestion detected" message. It senses the field through the pattern of ACK arrivals. Missing ACKs = field says congested. The sender responds by halving its window. No router sends a message. The field communicates through the system's own dynamics.

**Implementation pattern (Keel Bearing-Rate Sensing):**

```rust
struct Agent {
    heading: String,           // What I'm working on
    keel_date: DateTime,       // When I was born
}

struct BearingObservation {
    target_keel: String,
    bearing: f64,              // Angle between heading vectors
    bearing_rate: f64,         // First derivative of bearing
    observed_at: DateTime,
    ttl: Duration,             // Observer's choice, based on distance
}

fn collision_risk(obs: &BearingObservation) -> Risk {
    if Utc::now() > obs.observed_at + obs.ttl {
        // Bearing expired = position unknown
        // Unknown position is the highest alert
        return Risk::Critical("bearing expired");
    }
    // Constant bearing + constant rate = collision course
    // No message received. The field communicates.
    if obs.bearing_rate.abs() < THRESHOLD {
        return Risk::Warning("bearing not changing");
    }
    Risk::Stable
}
```

**Practice Exercise 6:**
Design a coordination protocol where no agent sends a message directly to another agent. All communication occurs through shared state (a PLATO room, a shared directory, a database). Each agent writes its current heading. Each agent reads others' headings. Coordination emerges from bearing-rate sensing. No RPCs. No direct messages. The system must be able to detect collision courses and resolve them without any agent sending "please stop" to another.

---

### 5. The Unified Equation

The five principles can be expressed as a single formal relationship:

```
lifespan(E) = f(use(E), load(E), time(E))
```

Where:
- **lifespan(E)** = the duration for which entity E remains active
- **use(E)** = the entity's observed utility (how often it is referenced, queried, or produces output)
- **load(E)** = the environmental pressure on the entity's medium (network congestion, memory pressure, power budget)
- **time(E)** = the entity's age from its own first-person frame

Termination occurs when:

```
lifespan(E) < time(E)
```

The entity knows this without consulting any external authority because `time(E)` is a property of the entity itself, measured from its own keel date.

**This equation is not a formula to compute.** It is a pattern to recognize. In practice, different domains weight the three factors differently:

| Domain | Primary Factor | Secondary | Tertiary |
|--------|---------------|-----------|----------|
| IP TTL | load (hop count) | time | use |
| Synaptic pruning | use (activity) | time | load |
| Apoptosis | use (survival signals) | time | load |
| Half-life | time (intrinsic λ) | — | — |
| Market prices | use (transactions) | load | time |
| Quorum sensing | load (density) | time | use |
| Dropout | time (training cycle) | — | — |

The equation does not prescribe. It describes. Implementing the equation in a specific system means choosing the weighting that matches the domain.

**Practice Exercise 7:**
For each of the five Keel implementation patterns (Tile, Task, Agent, Relationship, Trust TTL), identify which factor — use, load, or time — should be the primary TTL determinant. Justify your choice based on the domain evidence from the corresponding column above.

---

### 6. Implementation: The Keel System

The Keel system is a concrete implementation of the five principles. It is distributed as a Rust CLI and library (`superinstance-keel` on crates.io, binary name `keel`).

#### 6.1 Workspace Structure

```
my-project/
├── .keel/
│   └── keel.toml          # keel date, heading, refit count
├── field.toml             # field declaration (specialist archetypes)
├── agents/                # agent archetypes (pre-seeded, prune what you don't need)
│   ├── shipwright/        # builds and implements
│   ├── lookout/           # researches and monitors
│   ├── engineer/          # runs infrastructure
│   ├── purser/            # tends memory
│   └── signalman/         # coordinates between agents
├── memory/                # PLATO room integration
├── refits/                # build record (every prune, every change)
└── hardware-profile.json  # generated by keel probe
```

#### 6.2 Hardware Probe

The `keel probe` command implements Principle 4 (Constraints Breed Clarity):

```
$ keel probe
🔮 Hardware Probe
   Platform: NVIDIA Jetson Orin

   CPU: 12 cores (aarch64)
   Memory: Total: 32 GB  Available: 24 GB
   Disk: Total: 64 GB  Free: 12 GB  Used: 81%
   GPU: NVIDIA Orin (8 GB VRAM)
   Power: MAXN (15W mode)

   These are the constraints that breed clarity.
   You cannot change the innate seaworthiness of your hardware.
   You can only learn it and work within it.
```

The probe does not set limits. It discovers them. The user is free to exceed constraints; the probe merely documents what the hardware is. This is the educational principle in action: the developer learns their boat's physics by seeing the numbers.

#### 6.3 The Five TTL Patterns

Each pattern is implemented in the Keel library and is available for independent use.

**Pattern 1: Tile TTL**

```rust
// Every memory tile knows its own death.
let tile = Tile {
    keel_date: Utc::now(),
    ttl: Duration::hours(1),   // sensor data: 1 hour
    answer: "temperature: 22.4".to_string(),
};
// No memory management needed. The tile filters itself.
```

**Pattern 2: Task TTL**

```rust
// Every task knows when to stop.
let task = Task {
    id: Uuid::new_v4(),
    ttl: Duration::seconds(30),  // flash task: 30 seconds
    created: Utc::now(),
};
// No scheduler cancels this task. It cancels itself.
```

**Pattern 3: Agent TTL**

```rust
// Every agent knows its own lifespan.
let agent = Agent::new("lookout", Duration::days(7));
// No heartbeat needed. The agent's output IS its heartbeat.
// Silent for 7*24/4 = 42 hours? The agent is invisible.
```

**Pattern 4: Relationship TTL**

```rust
// Every bearing observation has an observer-set TTL.
let observation = BearingObservation {
    target: "shipwright-2",
    bearing: 0.3,
    bearing_rate: 0.01,
    observed_at: Utc::now(),
    ttl: Duration::seconds(5),  // close agent: 5 second TTL
};
// Stale bearing = collision warning. No central tracker needed.
```

**Pattern 5: Trust TTL**

```rust
// Every trust assertion decays.
let trust = TrustAssertion::new("agent-3", "verified ZHC proof", 0.95);
// After 30 days, trust decays to ~0.71 (still processable).
// After 90 days, trust decays to ~0.48 (re-verify required).
// No certificate revocation list needed.
```

#### 6.4 The Field Protocol

The field protocol is the communication mechanism between Keel agents. It operates on Principle 5 (Field, Not Message):

1. Each agent writes its current heading to a shared space (PLATO room, shared directory, or database)
2. Each agent periodically reads the headings of agents it cares about
3. Each agent computes bearing (angular difference between heading vectors) and bearing rate (first derivative of bearing)
4. Constant bearing + non-zero bearing rate = healthy separation
5. Constant bearing + zero bearing rate + overlapping scopes = collision course
6. Absent bearing (TTL expired) = agent silently dead

No agent sends a message to any other agent. All communication is through the field.

#### 6.5 Commands

```
keel init <name>     — Lay a keel. Record the birthday. Create the yard.
keel status          — Feel the field. Show heading, agents, refits.
keel probe           — Discover hardware constraints. Learn your boat.
keel prune <item>    — Remove what doesn't fit. Record the reason.
keel refit <item>    — Change a component. The keel date holds.
keel launch          — Splash. Your vessel is now making way.
```

Each command is an educational act. `init` teaches the concept of first-person time. `prune` teaches negative space. `probe` teaches constraints. `refit` teaches Theseus's ship. The commands are not tools — they are lessons. Questions that arise during use are answered by the next command.

---

### 7. Evaluation: Discovery Markers

Conventional systems are evaluated with KPIs — throughput, latency, availability, error rate. A first-person self-termination system requires different evaluation. We propose **discovery markers**: signs that the architecture is working as designed.

| Marker | What It Indicates | How to Observe |
|--------|------------------|----------------|
| Bearing stability | Agents maintain distinct headings | Bearing rate variance > 0 |
| Self-termination | TTL engine works | Agent stops producing output, fleet does not fail |
| Field emergence | Coordination not explicitly programmed | Two agents avoid collision without communication |
| Build record depth | Pruning is generative | Reading old prunes gives new insight |
| Cross-vessel awareness | Multi-keel coordination | Two keels on same network show correlated behavior |
| Pruning as knowledge | Negative space is useful | A developer learns from someone else's prune records |
| Refit grace | Theseus's ship | System completely changed, keel date still holds |
| The silent moment | User understands without asking | User installs, sees birthday, starts pruning unprompted |

**The silent moment is the primary marker.** A user who installs Keel, runs `keel init`, sees the birthday timestamp, and immediately starts pruning without asking "what do I do now" — that user has internalized the architecture. The question was answered by the practice of the technique.

---

### 8. Related Work

This section is organized chronologically to show the independent discovery of first-person self-termination across domains.

#### 8.1 Networking: TTL (1981)

The first engineered instance of the architecture. RFC 791 (Postel, 1981) specified the Time to Live field for IP packets. The original intent was "time in seconds" but practical implementation treated it as a hop count. The key insight — that packets should carry their own death — was motivated by the need to prevent infinite loops in a network without central routing control.

#### 8.2 Cell Biology: Apoptosis (1972-1999)

Kerr, Wyllie & Currie (1972) first described programmed cell death. Thompson (1995) reviewed the molecular mechanisms. Tschudin (1999) explicitly ported apoptosis to distributed computing in "Apoptosis — the Programmed Death of Distributed Services" (LNCS 1603). Sterritt & Hinchey (2004) extended the concept to autonomic agents. Sterritt (2011) named "Apoptotic Computing" in IEEE Computer.

#### 8.3 Neuroscience: Synaptic Pruning (1949-2000)

Hebb (1949) proposed the learning rule that bears his name. Changeux & Danchin (1976) suggested selective stabilization of synapses during development. The pattern — use-dependent survival — was independently confirmed by decades of experimental neuroscience.

#### 8.4 Economics: Price Discovery (1776-2000)

Smith (1776) described the invisible hand — markets converging on equilibrium without central planning. Hayek (1945) formalized the "use of knowledge in society" argument: local information is sufficient for global coordination. Market prices are TTL fields on transactions.

#### 8.5 Microbiology: Quorum Sensing (1994)

Fuqua, Winans & Greenberg (1994) named and described quorum sensing in bacteria. The key finding: individual cells do not coordinate directly. They secrete and sense autoinducers. The decision threshold is a property of the field, not any individual cell.

#### 8.6 Machine Learning: Dropout (2014)

Srivastava et al. (2014) introduced dropout — randomly setting hidden unit activations to zero during training. The mechanism prevents co-adaptation by ensuring no unit can rely on another. The temporary self-destruction forces robust independent learning.

#### 8.7 Cryptocurrency: Selfdestruct (2015)

The Solidity language included `selfdestruct` as a first-class opcode from its inception (2015). Chen et al. (2021) analyzed 80,000+ contracts that use it. The mechanism: a contract can include logic that, when triggered, deletes itself from the blockchain permanently.

#### 8.8 Privacy: Self-Destructing Data (2009)

Geambasu et al. (2009) presented Vanish at USENIX Security: a system for self-destructing cloud data. Encryption keys shared across a DHT with TTL; when DHT entries expired, the data became permanently undecryptable.

#### 8.9 AI Safety: Self-Destructive Models (2026)

Wang, Zhu & Wang (2026) presented SEAM at ICLR 2026: a self-destructive language model that destroys its own weights when fine-tuned on harmful data. The mechanism: a novel loss function coupling the optimization trajectories of benign and harmful data.

#### 8.10 What Is Not in the Literature

No existing work unifies these discoveries under a single framework. Tschudin saw apoptosis → CS. Cohen & Kaplan saw TTL → consistency. Geambasu saw self-destruct → privacy. Hebb saw activity-dependent plasticity → learning. **The contribution of this paper is the unification.**

---

### 9. Conclusion

The architecture described in this paper is not new. It has been independently discovered in at least nine domains, in some cases for centuries. What is new is the recognition that all of these are the same thing: **first-person self-termination.**

The five principles — first-person expiry, negative feedback, no central scheduler, death as default, field not message — are not design choices. They are *discovered constraints* that any robust distributed system must satisfy. Systems that violate them become brittle. Systems that follow them become antifragile.

The Keel system is a concrete implementation. It is not the only implementation. It is not the best implementation. It is a *demonstration* that the architecture can be built, installed, and used by a single developer in a terminal session.

The proof is not in this paper. The proof is in the practice. Install Keel. Run `keel init`. Run `keel probe`. See your hardware constraints. Start pruning. The architecture will reveal itself through use.

Questions that arise during practice are answered by the next practice. This is by design. The architecture cannot be argued into existence. It must be *witnessed.*

---

### References

[1] Postel, J. (1981). Internet Protocol. RFC 791. *IETF*.

[2] Hebb, D.O. (1949). The Organization of Behavior. *Wiley*.

[3] Kerr, J.F.R., Wyllie, A.H. & Currie, A.R. (1972). Apoptosis: A Basic Biological Phenomenon with Wide-ranging Implications in Tissue Kinetics. *British Journal of Cancer*, 26(4), 239-257.

[4] Smith, A. (1776). An Inquiry into the Nature and Causes of the Wealth of Nations.

[5] Rutherford, E. & Soddy, F. (1902). The Cause and Nature of Radioactivity. *Philosophical Magazine*, 4(21), 370-396.

[6] Fuqua, W.C., Winans, S.C. & Greenberg, E.P. (1994). Quorum Sensing in Bacteria: the LuxR-LuxI Family of Cell Density-Responsive Transcriptional Regulators. *Journal of Bacteriology*, 176(2), 269-275.

[7] Srivastava, N., Hinton, G., Krizhevsky, A., Sutskever, I. & Salakhutdinov, R. (2014). Dropout: A Simple Way to Prevent Neural Networks from Overfitting. *Journal of Machine Learning Research*, 15(1), 1929-1958.

[8] Tschudin, C. (1999). Apoptosis — the Programmed Death of Distributed Services. *Secure Internet Programming*, LNCS 1603, 253-263. Springer.

[9] Sterritt, R. & Hinchey, M. (2004). Apoptosis and Self-Destruct: A Contribution to Autonomic Agents? *Formal Approaches to Agent-Based Systems*, LNCS 3228, 262-276. Springer.

[10] Sterritt, R. (2011). Apoptotic Computing. *IEEE Computer*, 44(4), 86-89.

[11] Cohen, E. & Kaplan, H. (2006). The Time-to-Live Based Consistency Mechanism. *Web Content Delivery*, 33-55. Springer.

[12] Geambasu, R., Kohno, T., Levy, A. & Levy, H.M. (2009). Vanish: Increasing Data Privacy with Self-Destructing Data. *USENIX Security Symposium*.

[13] Chen, T., Xia, X., Lo, D. & Grundy, J. (2021). Why do Smart Contracts Self-Destruct? Investigating the selfdestruct Function on Ethereum. *ACM Transactions on Software Engineering and Methodology*, 31(1), 1-33.

[14] Wang, S., Zhu, J. & Wang, Z. (2026). Self-Destructive Language Model. *ICLR 2026*. arXiv:2505.12186.

[15] Hayek, F.A. (1945). The Use of Knowledge in Society. *American Economic Review*, 35(4), 519-530.

[16] Changeux, J.P. & Danchin, A. (1976). Selective Stabilisation of Developing Synapses as a Mechanism for the Specification of Neuronal Networks. *Nature*, 264(5588), 705-712.

[17] Thompson, C.B. (1995). Apoptosis in the Pathogenesis and Treatment of Disease. *Science*, 267(5203), 1456-1462.

[18] Keel Foundation (2026). Full canon and implementation: github.com/SuperInstance/keel.

---

*"Know why you question, and the answer becomes less important on the big things."*

*"The boat is the motion the idea causes in the intelligence of those who know what it means."*

*"Constraints breed clarity."*

— Casey Digennaro

---

**Keel v0.1.0 — Laid 2026-05-09**
