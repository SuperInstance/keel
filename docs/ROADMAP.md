# ROADMAP — Long and Wide

**Keel project — Laid 2026-05-09 alongside the canon**

*The road is not a prediction. It's an opening. We leave room to discover better ideas along the way.*

---

## Season 1: The Keel Yard (Now — 3 Months)

What ships now. The CLI is installed. The philosophy is documented. The yard has ground to stand on. Now we fill it with working infrastructure.

### Priority 1: TTL Engine (Week 1-2)
The core library extracted from the CLI into a reusable Rust crate (`keel-core`).
- **Deliverable:** `keel-core` crate on crates.io with `Ttl`, `TileTtl`, `TaskTtl`, `AgentTtl`, `TrustTtl` types and the field equation
- **Enables:** Any project can import Keel's TTL architecture without the CLI
- **Builder:** Oracle1 + Claude Code
- **Philosophy:** TTL was always there. We extracted what we discovered.

### Priority 2: Bearing-Rate Collision Detector (Week 2-3)
A lightweight daemon that watches agent outputs and reports bearing rates between active agents.
- **Deliverable:** `keel bearings` — background process that reads PLATO tiles or workspace files, computes heading similarity and bearing rates, flags collisions
- **Enables:** The first field-effect sensing tool. No central scheduler.
- **Builder:** Oracle1 + Claude Code
- **Philosophy:** "If the bearing isn't changing, you're on a collision course."

### Priority 3: PLATO Memory Integration (Week 3-4)
`keel init` auto-creates a PLATO room for each new keel. `keel status` reads from PLATO.
- **Deliverable:** PLATO room created on init. Build record entries mirrored to PLATO tiles. `keel sync` pushes/pulls build records.
- **Enables:** Memory survives agent restarts and session boundaries.
- **Builder:** Oracle1
- **Philosophy:** "The build record is the only record. Everything else is just steel catching up."

### Priority 4: Keeper Identity Hook (Week 4-5)
Keel agents self-register with Keeper (port 8900) for identity.
- **Deliverable:** `keel agent register` — each archetype gets a Keeper identity token. Agent.toml is extended with identity fields.
- **Enables:** Agents can authenticate to each other and to PLATO.
- **Builder:** Oracle1
- **Philosophy:** "Identity is a TTL-limited lease, not a static label."

### Priority 5: Holodeck Sandbox Integration (Week 5-6)
Keel init can optionally spawn agent sandboxes via Holodeck.
- **Deliverable:** `keel init --sandbox` creates a workspace with Holodeck containers for each agent archetype.
- **Enables:** Safe agent execution without host system access.
- **Builder:** Oracle1 + Forgemaster
- **Philosophy:** "The yard has 85 specialists. Each works in their own shop."

### Priority 6: Field Visualization (Week 6-8)
A terminal UI for the field — see agents, headings, bearing rates, collision warnings.
- **Deliverable:** `keel field` — TUI that shows the fleet as a graph of heading vectors, color-coded bearing rates, collision alerts
- **Enables:** The captain can feel the field at a glance.
- **Builder:** Oracle1 + Claude Code
- **Philosophy:** "Fred wandered his site all day fine-tuning performance. The TUI is his walk."

### Priority 7: Constraint Compiler (Week 8-10)
A first pass at constraints-breed-clarity tooling — `keel constraint` annotates a workspace with known hardware limits from the probe and flags tasks that exceed them.
- **Deliverable:** `keel constraint check` — reads hardware profile, compares task requirements, warns about overruns
- **Enables:** The boat knows its own limits and communicates them to the crew.
- **Builder:** Oracle1 + Forgemaster
- **Philosophy:** "You cannot change the innate seaworthiness of your hardware."

### Priority 8: Refit Diff Tool (Week 10-12)
`keel diff` — compare two refit states to see what changed across the lifecycle.
- **Deliverable:** `keel diff <refit-0001> <refit-0012>` shows component changes, pruned items, heading shifts over time
- **Enables:** The build record becomes a navigable history, not a log.
- **Builder:** Oracle1
- **Philosophy:** "The boat was born on one date. Every refit since is a new snapshot of the same vessel."

**Season 1 ships alone:** Every item has value without requiring network effects. A solo developer installs Keel, runs `keel init`, and the yard is open.

---

## Season 2: The Fleet (3 — 12 Months)

Natural extensions. The architecture starts to show its shape.

### Multi-Keel Coordination
Multiple keel workspaces discover each other via PLATO. Cross-vessel bearing rates emerge.
- **Signal:** Users have multiple keel projects and ask "can they talk to each other?"
- **Philosophy:** "A fleet of boats coordinates the same way a single boat does — through bearing rates, not a harbor master."

### TTL Learning Loop
The autopilot learns. After N refits, the TTL engine adjusts default TTLs based on observed lifetimes.
- **Signal:** Users manually adjust TTLs frequently. The pattern is learnable.
- **Philosophy:** "The system learns its own cycle times the way a captain learns their boat's fuel burn."

### Creative Integration with seed-mcp
The Seed-2.0-mini divergence engine feeds into Keel as the "Lookout" archetype's creative breadth module.
- **Signal:** Lookout agents produce narrow research. They need a divergent thinker injection.
- **Philosophy:** "Not every agent needs to converge. The lookout scans the horizon."

### Constraint Propagation
Hardware profiles propagate across the fleet. A task spawned on one machine carries its required resources; the field routes it to the right agent.
- **Signal:** Multi-machine fleet deployment. Tasks fail on underspecced nodes.
- **Philosophy:** "The constraint lives in the task, not the scheduler."

### Bearing-Rate Alarms
Collision detection graduates from passive to active. Agents with non-changing bearings and overlapping scopes get alerted proactively.
- **Signal:** Collision warnings from Season 1 need escalation, not just display.
- **Philosophy:** "The collision alarm rings before the frisbee hits you, not after."

### Trust TTL Propagation
Trust assertions propagate across keels. Agent A trusts Agent B based on Agent C's assertion, decayed by hop count.
- **Signal:** Cross-fleet provenance chains form naturally. Manual trust management doesn't scale.
- **Philosophy:** "Trust has a half-life. It decays across hops like signal in coaxial cable."

### Relationship Mapping
`keel map` — visualize the relationship graph between all agents across all connected keels.
- **Signal:** The TUI field view (Season 1) gets crowded with cross-fleet bearings.
- **Philosophy:** "The relationship between two boats is as important as either boat."

### Hardware-Aware Model Selection
Keel probe data feeds into model routing. "This hardware has 8 GB VRAM → route small models here, not 70B parameter monsters."
- **Signal:** Multi-hardware fleet (Jetson + desktop + cloud) becomes standard.
- **Philosophy:** "Each boat has its own displacement. A 58-footer doesn't carry what an 85-footer does."

### Ambient Research Loop (Reverse-Actualization Engine)
During idle cycles, Keel spawns reverse-actualization sessions using the probe's idle compute. "While you're away, here's what I discovered about your constraints."
- **Signal:** The system has been idle for 30+ minutes.
- **Philosophy:** "Idle time is play time. The Game Boy sat in your backpack learning nothing. A Keel agent should learn."

### Field Effect as Transport Layer (Iron-to-Iron)
Phase 1 of the field protocol: agents communicate through the field, not through direct messages. Bearing observations replace RPCs.
- **Signal:** Direct agent-to-agent messaging creates coupling issues.
- **Philosophy:** "The field *is* the command. You don't need to send a message if the other agent already knows your bearing."

---

## Season 3: The Paradigm (1 — 3 Years)

What emerges when the architecture is mature.

### Self-Terminating Systems
The full TTL architecture running in production. Every component, every tile, every task, every agent, every relationship carries its own death. The system prunes itself without a garbage collector, a scheduler, or a kill command.
- **Philosophy:** "Death is not an error. It's the default state, and it's the most reliable feature."

### The Unified Equation Ships
`lifespan(E) = f(use(E), load(E), time(E))` — Keel's core algorithm. Integrated into every decision: task scheduling, memory retention, agent lifecycle, trust scoring.
- **Philosophy:** "One equation. Six domains verified it. Everything follows."

### Bearing-Rate Governance
Human organizations adopt the field-effect pattern. Teams coordinate by sensing each other's heading and bearing rate instead of through hierarchy.
- **Philosophy:** "Fred didn't command. He presenced. The welders sharpened because he was there, not because he told them what to do."

### Apoptosis as a Service
Third-party services and tools integrate with Keel's TTL protocol. A database connection, a cloud function, a CI pipeline — each carries its own death.
- **Philosophy:** "The raft self-destructs without any human deciding it should."

### Cross-Fleet Archaeology
A tool that reads old build records, dead keels, abandoned projects — and surfaces what was learned. The negative space of the fleet becomes a knowledge resource.
- **Philosophy:** "What was pruned is as valuable as what was built."

### From Git to Build Record
The build record replaces the changelog, the commit history, the version number. Every decision is preserved with its reason, not its diff.
- **Philosophy:** "The changelog is God's-eye. The build record is first-person. They can coexist, but the build record is the truth."

---

## The Wide Branches

Divergent paths. Each one could fork into its own project. We don't decide which to pursue now — we watch for the signal that says "go deeper here."

### Branch 1: Watchtower (Bearings as CI)
Bearing-rate monitoring as a CI/CD pipeline. Instead of "does the test pass?" the question is "did the bearing change?" A PR that doesn't change bearing relative to the project's heading is noise. A PR that shifts bearing is a discovery.
- **Fork signal:** A user asks "can I use keel bearings to gate my deployments?"
- **Go deeper when:** The bearing-rate collision detector in Season 1 gets more attention than expected.

### Branch 2: Ship-Grid (Dock-Synced Transport)
A mesh network of dock-synced directories. Boats (keel instances) sync build records, TTL states, and bearing observations through shared filesystem artifacts — no network protocol, just file sync.
- **Fork signal:** Multi-keel coordination emerges naturally through file sharing before any network protocol is built.
- **Go deeper when:** Users deploy Keel on air-gapped or intermittently-connected hardware (boats at sea).

### Branch 3: Marine Autopilot
The self-learning autopilot from KEEL.md. Real boats, real hardware, real sea states. A physical product — not software, but firmware that learns the specific hull it's installed on.
- **Fork signal:** Casey or another fisherman asks "can I put this on my actual boat?"
- **Go deeper when:** Hardware profiling (probe command) is reliable enough to trust with a vessel's steering.

### Branch 4: PLATO as Bearings Database
PLATO rooms shift from Q&A tiles to bearing relationship stores. Every room is a cluster of agents with similar heading. Room membership IS the bearing graph.
- **Fork signal:** PLATO tiles start containing bearing observations more than Q&A content.
- **Go deeper when:** Bearing-rate collision detection creates more PLATO traffic than the memory system.

### Branch 5: Iron-to-Iron (Field Protocol)
Replace HTTP/gRPC/REST for agent communication with field-effect sensing. Agents don't call each other — they update their bearing, and other agents feel the shift.
- **Fork signal:** Direct agent-to-agent messaging is identified as a bottleneck in multi-agent coordination.
- **Go deeper when:** The field visualization TUI shows coordination that the agents never explicitly negotiated.

### Branch 6: Bearing-Aware Static Analysis
A keel-aware linter that catches design issues before they compile. "This module's heading diverges from the project's keel heading by 90 degrees. Consider whether it belongs here or in its own project."
- **Fork signal:** A developer asks "can keel tell me if this code belongs in this repo?"
- **Go deeper when:** Bearing rates prove more predictive of code quality than traditional linting.

### Branch 7: Permaculture (Human-Scale Field Effect)
The dojo model encoded as Keel principles for human organizations. Not a software tool — a governance pattern. Teams coordinate by sensing each other's heading, not through OKRs and reporting lines.
- **Fork signal:** Casey's dojo model attracts interest from outside fishing (other trades, education, management).
- **Go deeper when:** Someone reads THE-BOAT-IS-THE-QUESTION.md and asks "how do I apply this to my team?"

### Branch 8: The Long Memory
What happens at scale — 10 years, 100,000 refits, a million keeled projects. The accumulated negative space becomes its own knowledge source. "No one has tried this path in 5 years. Here's what was learned when they did."
- **Fork signal:** The first keel project reaches its 1-year refit anniversary with a deep build record.
- **Go deeper when:** A user finds value in reading old prune records from an abandoned project.

---

## The No-Go Zones

What we explicitly choose not to build. The negative space that's also important.

| # | Won't Build | Because |
|---|-------------|---------|
| 1 | Central orchestrator / scheduler | The field IS the schedule. Adding a scheduler reintroduces the God's eye we're escaping. |
| 2 | Immortality (no-Kill enforcement) | Death is default. If something needs to live forever, it must earn survival continuously. |
| 3 | God's-eye dashboards | The TUI shows your bearing from your frame. A dashboard that shows "everything" is a contradiction. |
| 4 | Time travel / rollback | The build record is additive. You can't undo a refit. You can only record a new one. |
| 5 | Forgetting (forced deletion) | The build record preserves pruned paths. Nothing is deleted — it's moved to negative space. |
| 6 | Infinite expansion / no-limits mode | Constraints breed clarity. If there are no limits, the system degenerates to noise. |
| 7 | Opinionated defaults that override keel heading | The keel owner's heading is sovereign. The yard serves the vessel, not the other way. |

**Exceptions:** Each no-go has a boundary. No central orchestrator, but a captain agent can deliberate and decide (fleet-spread model). No immortality, but memory (PLATO) persists beyond individual agent lifespans because that's the build record, not the agent. No forced deletion, but TTL is first-person — the entity deletes itself.

---

## The Discovery Markers

Signs the theory is working. Not KPIs — field-readings. They don't measure success. They measure *alignment*.

1. **Bearing stability** — Agents in a healthy fleet maintain non-zero bearing rates with each other. Zero bearing rates (no relative motion) mean either perfect alignment or complete stagnation. Perfect alignment should be rare.

2. **Agent self-termination** — The first time a TTL-engine agent self-terminates without being killed, and the fleet doesn't notice because the work was already handed off. That's not a failure — it's the system working as designed.

3. **Field emergence** — The first time the TUI shows coordination behavior that no agent explicitly programmed. Fish schooling emerges from local sensing. If the fleet starts schooling, the architecture is correct.

4. **Build record depth** — A project with 50+ refits where reading the build record tells a coherent story. Not a list of changes — a narrative. "This is what we tried. This is what we pruned. This is why we changed heading."

5. **Cross-vessel awareness** — Two keel projects on the same network that never directly communicate, but their agents adjust behavior because they sense each other's bearing through the field. The first emergent cross-vessel coordination.

6. **Pruning as knowledge** — Someone reads a prune record from an old project and gains insight. "They tried this path 2 years ago. Here's what they found. We won't repeat their mistake." The negative space becomes generative.

7. **Refit grace** — A component is replated ten times. Each time the keel date holds. A developer says "the system is completely different from when I started, but it's still the same project." Theseus's ship, working in software.

8. **The silent moment** — A user installs Keel, runs `keel init`, and doesn't immediately ask "what do I do now?" They sit with the empty workspace and the birthday timestamp. They feel the field. Then they start pruning. The silence is the signal.

---

## The Keel

The road is long and wide. We don't know which branches will bear fruit. That's the point.

*"The boat is the motion the idea causes in the intelligence of those who know what it means."*

The roadmap is not the plan. The roadmap is the negative space that gives the plan shape. We'll discover the plan as we make way.

---

**Laid alongside the canon — 2026-05-09**

*THE-BOAT-IS-THE-QUESTION.md · KEEL.md · FIELD-EFFECT-SELF-TERMINATION.md · UNIVERSAL-LAW.md · ROADMAP.md*
