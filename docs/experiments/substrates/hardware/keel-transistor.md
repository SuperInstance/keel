# Keel at the Physics Level — Transistor, DRAM, and Entropy

## The Thesis

> "A DRAM cell that isn't refreshed forgets. That IS death as default. The refresh signal IS the heartbeat. DRAM has been Keel-compatible since 1968."

The Keel architecture isn't just implementable in logic gates — it's already physically present in every semiconductor, naturally and unavoidably. The physics of the transistor IS the TTL engine. We've been building Keel hardware for 50+ years without realizing it.

---

## 1. Transistor Leakage — The Fundamental TTL

### The Physics

Every MOSFET has a subthreshold leakage current between source and drain when turned off:

```
I_leakage = I_0 × exp(V_GS / (n × V_T)) × (1 - exp(-V_DS / V_T))
```

This leakage is unavoidable. It's a consequence of quantum tunneling through the gate oxide and thermal carrier excitation. Even with zero gate voltage, charge bleeds away.

### TTL Interpretation

| Physical Effect | Keel Concept |
|-----------------|--------------|
| Gate capacitor charged → channel open | **Alive** — data is accessible |
| Charge leaks away over time → channel closes | **TTL exhaustion** — death approaches |
| Gate capacitor fully discharged → channel closed | **Dead** — data is gone |
| Gate refresh pulse | **Heartbeat** — periodic reassertion of life |
| Subthreshold leakage current | **The universal death timer** — entropy in silicon |

### Scale

```
Typical leakage per transistor (28nm process):
  I_leakage ≈ 1-100 pA per transistor

Time for gate charge to decay below threshold:
  τ_decay ≈ C_gate × V_th / I_leakage
  τ_decay ≈ 10^-15 F × 0.5V / 10^-11 A
  τ_decay ≈ 50 µs

Without refresh, a transistor "forgets" in microseconds.
This IS the transistor's built-in TTL.
```

**A transistor's leakage current IS the TTL of stored charge.** The silicon doesn't need a separate timer. The timer is the physics.

---

## 2. DRAM — The First Keel Memory

### How DRAM Works

A DRAM cell is:
- **1 transistor** (access switch)
- **1 capacitor** (storage)
- **Charge stored on capacitor** → bit value (1 = charged, 0 = discharged)

### The DRAM Death Timer

```
Capacitor charge decay:
  Q(t) = Q_0 × e^(-t / (R_leak × C))

For a typical DRAM cell:
  C = ~30 fF
  R_leak (through transistor) = ~10^15 Ω (theoretically)
  R_eff (with all leakage paths) = ~10^10 Ω
  
Time constant:
  τ = R_eff × C = 10^10 × 30 × 10^-15 = 300 µs

DRAM data retention (guaranteed):
  64 ms at 85°C (industry standard)
  100-500 ms at room temperature
```

**Key insight:** DRAM doesn't hold data forever. It holds data for 64 ms guaranteed, then bits start decaying. The JEDEC standard 64 ms refresh interval IS a heartbeat. Without it, DRAM dies.

### The 64 ms Rule — Universal Heartbeat Interval

```
Standard DRAM refresh:
  - 8192 rows per bank
  - Each row refreshed every 64 ms
  - That's one row every 7.8 µs
  - The refresh controller IS the heartbeat monitor
```

Every DRAM chip in every computer since 1970 has a built-in TTL of 64 ms, with a heartbeat controller that periodically resets that timer. We've been running Keel memory for half a century.

### DRAM as Keel Agent

```
DRAM Cell → Keel Mapping:
  Stored charge      → Agent state (alive data)
  Capacitor leakage   → Natural TTL (entropy)
  Row refresh signal  → Heartbeat (survival mechanism)
  Row not refreshed   → Death (data lost)
  Read after decay    → Stale data read (undefined bits)
  Bad row detection   → Death interrupt (ECC correction)
```

---

## 3. Floating Gate (EEPROM/Flash) — Trust as Stored Charge

### The Physics

A floating gate transistor has an extra polysilicon layer isolated by oxide:
- Charge injected through tunnel oxide (hot carrier injection / Fowler-Nordheim tunneling)
- Charge trapped on floating gate (no conductive path)
- Charge leaks over years via defect-assisted tunneling

### Trust as Charge

```
Data retention in Flash memory:
  - Spec: 10-100 year retention at 25°C
  - Actual: 1-5 year retention at 85°C
  - Leakage mechanism: Stress-Induced Leakage Current (SILC)

Charge decay:
  Q(t) = Q_0 × e^(-t / τ(T))
  
  Where τ(T) ≈ 10^8-10^9 seconds at 25°C (3-30 years)
        τ(T) ≈ 10^6-10^7 seconds at 85°C (weeks to months)
```

**A floating gate stores trust: charge decays over time.** The natural decay IS the trust TTL. Trust is a capacitor that leaks. Always has been.

### Trust TTL Mapping

```
Floating Gate Charge → Keel Trust:
  High charge level    → High trust (agent known, tested)
  Low charge level     → Low trust (agent distant, untested)
  Threshold voltage    → Trust boundary (reliable/unreliable)
  SILC (trap-assisted) → Trust erosion (small betrayals accumulate)
  Read disturb         → Trust damage from repeated queries
  Endurance cycles     → Trust limit (you burn out if refreshed too often)
```

---

## 4. SRAM — The Anti-TTL (Conscious Denial)

SRAM (6 transistors per cell) uses a latching feedback loop:
- No refresh needed — the feedback loop maintains state as long as power is ON
- SRAM does NOT self-terminate with power

### What SRAM Represents

SRAM is the architecture that _denies_ death. It actively fights entropy by consuming power to maintain state. SRAM is the equivalent of an immortal agent — it only dies when power is cut (catastrophic death).

### The Keel Critique of SRAM

```
Power ON  → SRAM holds data *forever* → Artificial immortality → Expensive (6T/cell)
Power OFF → SRAM loses everything    → Catastrophic death     → No natural decay

Keel version:
  DRAM would be the "natural" memory — it accepts death gracefully
  SRAM is the "unnatural" choice — it fights death at the cost of density
```

---

## 5. The Quantum Level — TTL as Uncertainty

### Quantum Mechanical Leakage

At the quantum level, information leakage is fundamental:

```
Gamow factor (tunneling probability):
  P_tunnel ≈ exp(-2 × d × sqrt(2m × (V_0 - E)) / ħ)
  
Where:
  d = oxide thickness  (≈ 1.5 nm in modern nodes)
  V_0 - E = barrier height (≈ 3.1 eV for SiO₂)
  m = electron mass
  ħ = reduced Planck constant
```

Even with perfect oxide, electrons tunnel through with non-zero probability. Information loss is quantum-mechanically guaranteed.

**The universe IS the TTL engine (entropy).** Every physical system degrades toward equilibrium. There is no undirected, lossless, permanent data storage in the physical universe.

### Second Law of Thermodynamics as TTL

```
ΔS_universe > 0 (irreversible processes)
  
  Every computation generates heat
  Every bit flip requires energy dissipation (Landauer's principle)
  Every memory refresh consumes power to fight entropy

  The refresh cycle is literally work against the Second Law.
  The TTL is the measurement of how much work you're willing to do
  to keep death at bay.
```

---

## 6. Summary — The Physics of Death

| Technology | Death Mechanism | TTL | Heartbeat | Death Style |
|------------|----------------|-----|-----------|-------------|
| **Transistor** | Leakage current | µs | Gate refreshes | Gradual decay |
| **DRAM** | Capacitor discharge | 64 ms | Row refresh | Predictable death |
| **Flash** | SILC / tunnel leakage | 1-100 years | Program/erase | Slow fading |
| **SRAM** | Power loss | ∞ (with power) | Continuous current | Catastrophic |
| **Quantum** | Barrier tunneling | Probabilistic | Measurement | Inevitable |

### The Universal Truth

Every physical data storage medium in existence has a built-in TTL. The only difference between technologies is:

1. **How long** until data decays naturally (the TTL duration)
2. **What mechanism** you use to extend life (the heartbeat)
3. **How much energy** you're willing to spend to delay death

The Keel architecture doesn't _add_ death to computing. Death was always there. Keel just stops pretending it isn't.

---

## Practical Implication

You can build a Keel system TODAY using off-the-shelf DRAM:

```
Standard DDR4 DIMM + custom refresh controller:
  Normal DRAM: refreshes all rows every 64 ms
  Keel DRAM:   selectively refuses refreshes for expired agents
               each row is an agent with its own refresh schedule
               unrefreshed rows die → reads return undefined → ERROR
```

This is exactly the architecture described in the TTL CPU design, now realized as: **every DRAM row IS a TTL register**. The memory controller IS the field. A row that doesn't get a heartbeat (refresh) dies. Reading a dead row asserts the error line.

**DRAM has been Keel-compatible since 1968.**
