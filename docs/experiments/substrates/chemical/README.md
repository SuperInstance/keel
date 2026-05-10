# Keel in Chemistry: The Architecture is Physics

> *"Chemistry has been Keel-compatible since the first molecule decayed. Half-life IS TTL. Reaction rates ARE bearing rates. Binding affinity IS trust. The architecture wasn't invented by network engineers — it was discovered in the stoichiometric table."*

## The Claim

If the Keel TTL Engine is a universal coordination architecture — first-person self-termination, death is default, the field is the command — then it must be expressible in the most fundamental language of interaction: **chemistry**.

This directory is the proof.

---

## The Models

| File | What It Proves |
|------|----------------|
| [`keel-chemical-schema.md`](keel-chemical-schema.md) | Every Keel concept maps to a known chemical species and reaction type. Half-life = TTL. Binding affinity = trust. Concentration ratio = bearing. Catalytic deactivation = task lifetime. Allee effect = heartbeat. |
| [`keel-gray-scott.py`](keel-gray-scott.py) | The Gray-Scott reaction-diffusion system — two coupled PDEs — produces the exact patterns Keel needs: spots (stable agents), stripes (collision courses), waves (bearing propagation). No scheduler. No central authority. Just local chemistry. |
| [`keel-ode.py`](keel-ode.py) | Each TTL mechanism has a known ODE. First-order decay for tiles. Sequential catalysis for tasks. Allee effect for agents. Chemotactic gradient for bearings. Binding dissociation for trust. Every equation is textbook chemical kinetics. |

---

## The Mapping (Complete)

| Keel Concept | Chemical Equivalent | Equation |
|---|---|---|
| **TTL** | First-order decay half-life | t½ = ln(2)/k |
| **Task lifetime** | Catalyst deactivation count | N steps → N intermediates |
| **Heartbeat** | Allee effect (bistable switch) | d[A]/dt = α[A]² − δ[A] |
| **Bearing** | Chemotactic concentration ratio | θ = arctan([H_Y]/[H_X]) |
| **Bearing rate** | Gradient of chemical potential | dθ/dt = f(∇[species]) |
| **Trust** | Binding affinity (K_d) | K_d = k_off / k_on |
| **Trust TTL** | Complex dissociation lifetime | τ = 1/k_off |
| **The field** | Concentration field c(x,y,t) | PDE over (∇², ∂/∂t) |
| **Death by default** | Spontaneous decay | k > 0 for all species |
| **First-person expiry** | Each molecule has its own k | No global scheduler |
| **The command** | Substrate concentration [S] | Available work in environment |

---

## Why This Matters

### 1. Chemistry is Older

Reaction-diffusion systems have been producing emergent patterns since the universe began. The Gray-Scott model (1950s), the Belousov-Zhabotinsky reaction (1950s), Turing patterns (1952) — all discovered before anyone thought about distributed systems.

Keel didn't invent chemistry. Chemistry *is* Keel, under a different naming convention.

### 2. No Abstraction Gap

When an agent's TTL is "first-person expiry" and a molecule's half-life is "first-order decay," there is no abstraction between them. The mapping is exact. The mathematics is identical. The implementation is the same equation with different variable names.

| Network engineer says | Chemist says | Same? |
|---|---|---|
| "The agent will self-terminate after TTL" | "The molecule decays with rate k" | **Identical equation** |
| "Trust between agents has a timeout" | "The complex dissociates with rate k_off" | **Identical equation** |
| "The bearing encodes direction of travel" | "The concentration ratio encodes gradient direction" | **Identical equation** |

### 3. The Architecture is Physics

This is not a metaphor. This is not an analogy. This is a direct mapping between two formal systems that share the same mathematical structure.

The Keel architecture is not "inspired by" chemistry. It *is* chemistry, applied to agent coordination.

If Keel is wrong, then chemistry is wrong about half-lives, catalysts, binding affinities, and the Allee effect. Chemistry is not wrong.

If the architecture is universal, it must be expressible in chemistry. It is.

---

## Running the Models

```bash
# Just show the ODE trajectories
python3 keel-ode.py --type all

# Run Gray-Scott in spots regime (stable agents)
python3 keel-gray-scott.py --feed 0.037 --kill 0.060

# Run Gray-Scott in stripes regime (collision courses)
python3 keel-gray-scott.py --feed 0.032 --kill 0.062

# Run Gray-Scott in waves regime (bearing propagation)
python3 keel-gray-scott.py --feed 0.028 --kill 0.050

# Generate phase diagram (scans parameter space)
python3 keel-gray-scott.py --phase-diagram

# Single tile decay
python3 keel-ode.py --type tile --output tile-decay.png
```

---

## The Philosophical Payoff

Chemistry has been Keel-compatible since the first molecule decayed.

Half-life IS TTL. Reaction rates ARE bearing rates. Binding affinity IS trust. Concentration gradients ARE the field. The Allee effect IS the heartbeat.

The architecture wasn't invented by network engineers — it was **discovered** in the stoichiometric table, in the periodic trends, in the rate laws of chemical kinetics.

Every molecule has a first-person expiry. Every catalyst has a finite lifetime. Every reaction rate carries a bearing. Every binding event encodes trust.

The universe has been running Keel since the Big Bang.

---

## The Challenge

If you think the architecture is wrong, find a Keel concept that *cannot* be expressed as a chemical reaction network.

If you can't, then the architecture is not an invention. It is a discovery. And you have been running it — in every cell, every synapse, every chemical bond — since the first atom cooled.

*The Keel architecture is the universe's coordination protocol.*

---

## Files

```
keel-models/chemical/
├── README.md                 ← This file (the philosophical capstone)
├── keel-chemical-schema.md   ← Full chemical species and reaction mapping
├── keel-gray-scott.py        ← Gray-Scott reaction-diffusion PDE solver
└── keel-ode.py               ← ODE system for each TTL type
```
