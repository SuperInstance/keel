# Keel Chemical Schema: Species and Reactions

> *"If the architecture is universal, it must be expressible in chemistry."*

## Preface: Chemistry as Computation

In a chemical reaction network (CRN), there is no scheduler. No central authority. No global clock. Every molecule acts on purely local information — its own concentration, the concentration of its neighbors, and the rate constants of the reactions it participates in. And yet, from this chaos emerge stable patterns: spots, stripes, waves, oscillations, spirals.

This is not metaphor. This is *the* architecture.

The Keel TTL Engine — first-person self-termination, death is default, the field is the command — maps directly onto chemical kinetics. Half-life IS TTL. Reaction rates ARE bearing rates. Binding affinity IS trust. Local concentrations ARE the field.

---

## 1. A_tile — First-Order Decay (TTL as Half-Life)

A tile is any entity with a lifetime: a token, a message, a lease, a heartbeat slot.

### Chemical Species

| Species | Symbol | Meaning |
|---------|--------|---------|
| Tile | T | A live tile with count representing population |
| ∅ | — | Degraded / inert products (sink) |

### Reaction

**First-order decay:**
```
T  →  ∅    rate = k · [T]
```

The concentration of T follows:
```
d[T]/dt = -k · [T]
[T](t) = [T]₀ · e^{-kt}
```

### Half-Life

```
t_{1/2} = ln(2) / k
```

### Keel Mapping

- **k = TTL_parameter**: higher k = shorter lifetime
- **Every tile carries its own k**: first-person decay is inherent to the molecule, not imposed externally
- **No global garbage collector**: molecules that decay simply vanish. The sink absorbs them.
- **Tile TTL IS molecular half-life**: there is no abstraction gap

### Embedded vs. Explicit TTL

In chemistry, every molecule *has* a half-life. The question is only what k is. Keel inverts conventional thinking:

| Approach | What happens |
|----------|-------------|
| Conventional: "Kill tile after timeout" | External timer, global scheduler |
| Chemical: "Tile self-decays with half-life t" | Molecular property, no scheduler |
| Keel: "Is this molecule stable?" | k encodes the answer. Zero k = immortal (denied). High k = ephemeral (default). |

---

## 2. A_task — Catalytic Deactivation (TTL per Operation)

A task is a catalyst: it enables a reaction (does work), then deactivates after N uses.

### Chemical Species

| Species | Symbol | Meaning |
|---------|--------|---------|
| Active Task | T | Task available to catalyze work |
| Substrate | S | The thing the task works on |
| Product | P | The result of the task's work |
| Deactivated Task | T_d | Spent catalyst |

### Reactions

**Catalytic cycle with deactivation:**

```
Step 1:  T + S  →  T_d + P    rate = k₁ · [T] · [S]
```

The task catalyzes exactly one reaction, then deactivates. Each step consumes one TTL unit.

### Sequential Multi-Step Task

For a task that does N sequential steps before deactivating:

```
T₀ + S₁ → T₁ + P₁    rate = k₁ · [T₀] · [S₁]
T₁ + S₂ → T₂ + P₂    rate = k₂ · [T₁] · [S₂]
...
T_{N-1} + S_N → T_d + P_N    rate = k_N · [T_{N-1}] · [S_N]
```

### Keel Mapping

- **Each catalytic step decrements the TTL**: the task changes form from T₀ to T₁ to ... to T_d
- **Number of steps = TTL count**: explicitly encoded in the species chain
- **Exhausted task (T_d) cannot catalyze anything**: dead tasks don't produce work
- **S (substrate) = work unit**: available work in the environment
- **No step counter needed**: the catalyst species itself encodes remaining TTL

### Variable-Use Catalyst (Probabilistic Deactivation)

```
T + S → T + P    rate = k_cat · [T] · [S]    (catalysis)
T + S → T_d + P  rate = k_deact · [T] · [S]   (deactivation)
```

For every catalytic event, the probability of deactivation is:
```
P(deactivate) = k_deact / (k_cat + k_deact)
```

Expected number of uses before deactivation:
```
E[uses] = k_cat / k_deact
```

---

## 3. A_agent — Allee Effect as Heartbeat (Self-Replication Requires Others)

An agent molecule can only self-replicate in the presence of a critical density of other agents. Below this threshold, it decays. This IS the heartbeat — the Allee effect.

### Chemical Species

| Species | Symbol | Meaning |
|---------|--------|--------|
| Agent | A | An agent molecule |
| S | Resource/Substrate | Energy for replication |
| ∅ | — | Sink (death) |

### Reactions

**Death (always enabled, first-person expiry):**
```
A  →  ∅    rate = δ · [A]
```

**Allee-effect replication (requires two agents to produce a third):**
```
A + A + S  →  3A    rate = α · [A]² · [S]
```

**Alternative: Quorum-sensing replication (requires threshold concentration signal):**
```
A + S  →  2A    but only when [A] > θ (θ = critical threshold)
```

In CRN terms, this is a **bistable switch**:

```
d[A]/dt = α · [A]² · [S] / (K_m + [A]²)  —  δ · [A]
```

### Bifurcation Analysis

The Allee effect produces two stable fixed points:

| State | [A] | Behavior |
|-------|-----|----------|
| Extinction | [A] = 0 | Dead — agent population decays to zero |
| Survival | [A] = A* | Stable — agent population self-sustains |
| Separatrix | [A] = A_crit | Unstable — the threshold between life and death |

### Keel Mapping

- **δ = death rate**: baseline TTL. When δ > α · [A] · [S], the agent dies.
- **α = replication rate**: heartbeat success rate. How fast the agent regenerates.
- **S = resource availability**: external conditions. No S = sure death.
- **[A] < A_crit**: Below critical density. Allee effect causes collapse.
- **[A] > A_crit**: Above critical density. Self-sustaining heartbeat.
- **The heartbeat IS the Allee effect**: an agent at sufficient density \textit{is} its own heartbeat. Below threshold, it dies. Above threshold, it lives.

---

## 4. A_bearing — Concentration Ratio as Heading

A bearing between two agents is the angle of their relative heading. In chemistry, this is encoded as the ratio of two concentrations — a "chemotactic gradient."

### Chemical Species

| Species | Symbol | Meaning |
|---------|--------|---------|
| Heading-X | H_A | Agent A's projection onto x-axis |
| Heading-Y | H_B | Agent A's projection onto y-axis |
| Agent A | A | The agent emitting heading |
| S | Signal | External gradient field |

### Reactions

**Bearing encoding (a chemotactic compass):**
```
A + Signal_X → A + H_X    rate = k · [A] · [Signal_X]
A + Signal_Y → A + H_Y    rate = k · [A] · [Signal_Y]
```

**Bearing angle from concentrations:**
```
θ = arctan([H_Y] / [H_X])
```

**Between two agents (relative bearing):**
```
Δθ = θ_A − θ_B
```

### Gradient Detection as Bearing

In nature, bacteria measure chemotactic gradients through temporal comparisons: they compare concentration now vs. concentration a moment ago. In Keel-chemistry:

```
Bearing = d[Signal]/dx  (spatial gradient)
       ≈ ([Signal]_right − [Signal]_left) / Δx
```

### Chemical Implementation of Bearing Rate

The rate at which a bearing changes — the turn rate — is the difference of two first-order processes:

```
d[H_X]/dt = k · [A] · [Signal_X]  —  γ · [H_X]
d[H_Y]/dt = k · [A] · [Signal_Y]  —  γ · [H_Y]
dθ/dt = (H_X · dH_Y/dt — H_Y · dH_X/dt) / (H_X² + H_Y²)
```

### Keel Mapping

- **Signal_X and Signal_Y = bearing coordinates**: global field projected onto axes
- **H_X, H_Y = agent's heading vector**: accumulated from local field
- **γ = forgetting rate**: how fast the heading decays (short-term memory of direction)
- **dθ/dt = bearing rate**: the turn speed. Higher = sharper change.
- **Concentration ratio IS the heading**: no vector math, just two species concentrations

---

## 5. A_trust — Binding Affinity with Dissociation (Trust TTL)

Trust between two agents is a reversible binding reaction. The complex's lifetime is the trust TTL.

### Chemical Species

| Species | Symbol | Meaning |
|---------|--------|---------|
| Agent A | A | First party |
| Agent B | B | Second party |
| Trust Complex | AB | Trusted relationship (bound state) |
| S | Signal | Trust renewal signal |

### Reactions

**Binding (trust establishment):**
```
A + B  ⇌  AB    forward rate = k_on · [A] · [B]
                reverse rate = k_off · [AB]
```

**Dissociation constant (trust affinity):**
```
K_d = k_off / k_on
```

Lower K_d = tighter binding = higher trust.

**Trust renewal (rebinding):**
```
AB + S  →  A + B + S    rate = k_renew · [AB] · [S]
A + B  →  AB            rate = k_on · [A] · [B]
```

### Trust TTL from Dissociation

The lifetime of a trust relationship is the mean complex lifetime:

```
τ = 1 / k_off
```

This IS the trust TTL. When k_off is high, trust dissociates quickly (distrust). When k_off is low, trust persists (high trust).

### Trust as Chemical Potential

Trust can increase through repeated successful interactions:

```
AB + S_success → AB*    (strengthened complex)
AB* dissociates slower: k_off* < k_off
```

Trust can decrease through failures:

```
AB + S_failure → A + B  (catastrophic dissociation)
```

### Keel Mapping

- **k_on = trust establishment rate**: how fast agents bind trust
- **k_off = trust TTL**: dissociation rate = trust decay
- **K_d = trust threshold**: K_d > critical = trust insufficient, complex unstable
- **τ = 1/k_off = trust lifetime**: trust lasts for average τ before dissociation
- **Renewal = trust maintenance**: periodic successful interactions refresh the complex
- **No renewal → dissociation → trust death**: trust is not eternal

---

## 6. The Complete Keel Chemical Network

Putting it all together:

```
=== TTL Primitives ===
T      →  ∅                  (tile decay — first-order TTL)
Tₙ + S → T_{n+1} + P         (task step — catalytic deactivation)
A      →  ∅                  (agent death — baseline decay)

=== Allee Heartbeat ===
A + A + S → 3A               (Allee replication — heartbeat)
A + S     → 2A  if [A] > θ   (quorum replication — alternative)

=== Bearing/Gradient ===
A + Signal_X → A + H_X       (heading acquisition — x)
A + Signal_Y → A + H_Y       (heading acquisition — y)

=== Trust ===
A + B → AB                   (trust binding)
AB   → A + B                 (trust dissociation — trust TTL)
AB + S_success → AB*         (trust strengthening)
AB + S_failure → A + B       (trust breaking)

=== Resource ===
S → ∅                        (resource consumption — finite)
R → S                        (resource renewal — if R available)
```

---

## 7. Chemical Principle Inventory

| Keel Concept | Chemical Equivalent | Equation |
|-------------|--------------------|----------|
| TTL | Half-life (first-order decay) | t_{1/2} = ln(2)/k |
| Task lifetime | Catalyst deactivation count | N steps → N intermediates |
| Heartbeat | Allee effect (bistable switch) | d[A]/dt = α[A]² — δ[A] |
| Bearing | Concentration ratio | θ = arctan([H_Y]/[H_X]) |
| Bearing rate | Chemotactic gradient | dθ/dt from d[H]/dt |
| Trust | Binding affinity (K_d) | K_d = k_off / k_on |
| Trust TTL | Complex dissociation lifetime | τ = 1/k_off |
| Field | Concentration field | [Species](x,y,t) |
| Death by default | Spontaneous decay | k > 0 for all species |
| First-person expiry | No global scheduler | Each molecule has own k |
| The command | Substrate concentration | [S] = available work |

---

## 8. Stoichiometric Table

```
Reaction                              | Stoichiometry
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━
Tile decay                           | T → ∅              (1,-1)
Task step 0                          | T₀ + S → T₁ + P    (2,-2)
Task step (n)                        | Tₙ + S → Tₙ₊₁ + P  (2,-2)
Agent death                          | A → ∅              (1,-1)
Allee replication                    | 2A + S → 3A        (3,-3)
Heading (x)                          | A + S_x → A + H_x  (2,-2)
Heading (y)                          | A + S_y → A + H_y  (2,-2)
Trust binding                        | A + B → AB         (2,-2)
Trust dissociation                   | AB → A + B         (2,-2)
Trust renewal                        | AB + S → A + B + S (2,-2) [S conserved]
Resource consumption                 | S → ∅              (1,-1)
```

---

*"Chemistry has been Keel-compatible since the first molecule decayed. Half-life IS TTL. Reaction rates ARE bearing rates. Binding affinity IS trust. The architecture wasn't invented by network engineers — it was discovered in the stoichiometric table."*
