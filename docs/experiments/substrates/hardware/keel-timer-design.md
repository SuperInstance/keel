# Keel Timer Design — 555 Timer Circuits

## The 555 Timer as TTL Engine

The 555 timer IC IS the physical embodiment of the Keel TTL concept:

- **Monostable mode**: Trigger once, output HIGH for a set duration, then automatically LOW. Death is default.
- **Astable mode**: Oscillates as long as RESET is HIGH. RESET goes LOW → oscillation stops. Survival depends on an active heartbeat signal.

Both are second-person self-termination — the circuit _is_ the death mechanism, not an instruction that kills.

---

## 1. TileTtl — Monostable 555 (One Shot, One Death)

**Concept**: A tile is triggered once, does its work for N ms, then dies. No second trigger. Single-use data.

### Circuit

```
                    +---+
        +-----------|VCC|---+
        |           +---+   |
        |               |   |
        |               [R1]
        |               |   |
    +---+---+          +---+---+
    |TRIGGER|----------|THRESH   |  (pin 6 connected to pin 2 for monostable)
    |       |          +---+----+
    +---+---+              |  +-----+
        |                  +--|DISCH|
    (trigger pulse)           +--+--+
                                |
                                [C1]
                                |
                               GND

        Output: pin 3 ────────► Data Valid line
```

### Timing

```
T_high = 1.1 × R1 × C1

Example values:
  R1 = 100kΩ, C1 = 10µF  →  T_high = 1.1s
  R1 = 10kΩ,  C1 = 1µF   →  T_high = 11ms
  R1 = 470Ω,  C1 = 1nF   →  T_high = 517ns (near silicon speed)
```

### Behavior

```
       Trigger __|‾‾|____
                    ______________
Output  ___________|              |___
                    ↑             ↑
                Output HIGH   Output goes LOW 
                (Alive)       permanently (Dead)
```

- Trigger once, output stays HIGH for T_high, then LOW forever
- No amount of retriggering changes the period (standard monostable)
- When output goes LOW, the associated data becomes invalid

### TTL Counter Mapping

| 555 Component | Keel Concept |
|---------------|--------------|
| R1 | Lifetime constant (scale) |
| C1 | Lifetime constant (duration) |
| TRIGGER | Birth event (write to register) |
| Output HIGH | Alive (TTL > 0) |
| Output LOW | Dead (TTL = 0) |
| DISCH pin | Self-termination mechanism |

---

## 2. AgentTtl — Astable 555 with Reset Gate (Heartbeat)

**Concept**: An agent stays alive as long as its RESET pin stays HIGH. Drop RESET LOW → oscillation stops → agent dies. The agent's own code must periodically pulse the RESET pin (heartbeat).

### Circuit

```
                    +---+
        +-----------|VCC|---+
        |           +---+   |
        |               |   |
        |            +--[R1]-+
        |            |       |
        |            +--[R2]-+
        |            |       |
    +---+---+       |   +---+---+
    |RESET  |-------+---|THRESH  |
    |(heartbeat)    |   +---+----+
    |               |       |  +-----+
    +---+---+       +-------+--|DISCH|
        |                      +--+--+
        |                         |
        |           +----+        |
        |           |    |        |
        |       +---+    |        |
        |       |    |   |        |
        |       |  +---+---+      |
        |       |  |TRIG  |-------+
        |  +----+  +---+---+
        |  |            |
        +--+----[C1]----+
                 |
                GND

        Output: pin 3 ────────► Heartbeat clock / Alive signal
```

### Timing

```
Frequency f = 1.44 / ((R1 + 2×R2) × C1)
Duty cycle = R1 / (R1 + R2)  (time HIGH)

Example values:
  R1 = 1kΩ, R2 = 10kΩ, C1 = 10µF  →  f ≈ 6.8 Hz, 9% duty
  R1 = 10kΩ, R2 = 100kΩ, C1 = 1µF →  f ≈ 6.5 Hz
  R1 = 1kΩ, R2 = 100kΩ, C1 = 1nF  →  f ≈ 7 kHz
```

### Behavior

```
               ________    ________    ________
RESET _________|heartbeat|_|heartbeat|_|heartbeat|___
                                                    
Output /\/\/\/\/\/\/\/\/\/\/\/\/\/\/\_______________
                                    ↑
                                RESET goes LOW
                                Oscillation stops
                                Agent is dead
```

- Oscillates freely when RESET is HIGH
- Stops oscillating (output LOW) when RESET goes LOW
- Agent must toggle RESET to stay alive — that's the heartbeat

### Heartbeat Failure Detection

```
If output goes LOW for > 2× T_period:
  → Downstream logic detects missing clock pulses
  → Error line asserts
  → Register entry for this agent goes stale
```

### TTL Counter Mapping

| 555 Component | Keel Concept |
|---------------|--------------|
| RESET pin | Heartbeat signal |
| R1, R2, C1 | Agent's inherent TTL characteristics |
| Oscillating output | Agent is alive and working |
| Flat LOW output | Agent is dead |
| Frequency | Agent's processing speed / cadence |

---

## 3. BearingTtl — Dual 555 with Coupled Timing (Collision Detection)

**Concept**: A bearing is the relationship between two agents. Two 555 timers run independently. If one stops before the other, a collision output fires. This detects asymmetry — one agent dying before its partner.

### Circuit

```
555 #1 (Agent A) ──┬───► Alive_A
                   │
    +--[R_a]--[C_a]│
    │              │
    +---[R_b]--[C_b]
    │              │
555 #2 (Agent B) ──┴───► Alive_B

                +-----------------+
Alive_A ────────| AND (inverted)  |──── Collision_High
                | A AND NOT B     |
NOT_Alive_B ────|                 |
                +-----------------+

                +-----------------+
NOT_Alive_A ────| AND (inverted)  |──── Collision_Low
                | NOT A AND B     |
Alive_B ────────|                 |
                +-----------------+

                +-----------------+
Collision_High ─|      OR         |──── COLLISION_OUT
Collision_Low ──|                 |
                +-----------------+
```

### Behavior

```
Normal state (both alive):
  A: /\/\/\/\/\/\/\/\/\/
  B: /\/\/\/\/\/\/\/\/\/
  COLLISION: LOW

Agent A dies:
  A: /\/\/\/\______________
  B: /\/\/\/\/\/\/\/\/\/\/
  COLLISION: HIGH ──► Collision! Bearing broken.

Both die at same time:
  A: /\/\/\____________
  B: /\/\/\____________
  COLLISION: LOW (no asymmetry — clean death)
```

### TTL Counter Mapping

| 555 Component | Keel Concept |
|---------------|--------------|
| 555 #1 | One agent in the bearing |
| 555 #2 | The other agent in the bearing |
| COLLISION | Bearing integrity broken |
| Both dead | Clean dissolution (bearing terminated cleanly) |
| One dead, other alive | Collision! Relationship failure |

---

## 4. TrustTtl — RC Circuit with Charge/Decay (Trust Grows, Trust Decays)

**Concept**: Trust is analog — it accumulates over time and decays when connection is lost. An RC circuit naturally implements this: capacitor charges through a resistor (trust builds), discharges when disconnected (trust decays).

### Circuit

```
                    +---+
                    |VCC|
                    +---+
                       |
                    +--[R_charge]--+
                    |              |
                    |          +---+---+
+-----+             |          |COMPARATOR|──── Trust_Level (HIGH/LOW)
|REFRESH|-----------|          |(+ input)|
|(heartbeat)|        |          +---+---+
|        |           |              |
+-----+              |          +---+---+
                    +----[C1]---|(- input)|
                                | V_ref   |
                    GND-------> |         |
                                +---------+
```

### Timing

```
Charge (trust building):
  V(t) = VCC × (1 - e^(-t / (R_charge × C1)))

Decay (trust fading):
  V(t) = V_initial × e^(-t / (R_decay × C1))

Example values:
  R_charge = 100kΩ, R_decay = 1MΩ, C1 = 10µF
  τ_charge = 1s (90% in ~2.3s)
  τ_decay = 10s (to 37% in 10s)
```

### Behavior

```
REFRESH pulses ██  ██  ██  ██  ██  ██  ██
                  ___________________________
Trust V(t)       ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁‾‾‾‾‾
                              ↑     ↑
                          Trust exceeds    Trust drops below
                          threshold →      threshold →
                          HIGH output      LOW output

Disconnected:      Trust Decay
                   ████████████████
                   ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾▁▁▁▁▁▁▁▁▁
                                              ↑
                                          Trust decays below
                                          threshold
```

### Design Notes

- **R_charge < R_decay**: Trust builds faster than it decays (asymmetric — trust is easier to lose than gain)
- **Diode in discharge path**: Allows fast charge, slow decay (or vice versa)
- **Schmitt trigger on output**: Prevents oscillation near threshold
- **Capacitor leakage** IS the TTL effect — no capacitor holds charge forever

### TTL Counter Mapping

| 555 Component | Keel Concept |
|---------------|--------------|
| Refresh pulses | Heartbeats / interactions |
| Capacitor voltage | Trust level |
| R_charge | Trust-building rate |
| R_decay | Trust-decay rate |
| Comparator threshold | Trustworthiness boundary |
| Natural leakage | Entropy: trust eventually decays even with perfect connections |

---

## Universal Insight

Every 555 timer circuit is a different face of the same truth:

- **Monostable**: Death is guaranteed after one lifetime
- **Astable**: Life is maintained by continuous heartbeat; stopping means death
- **Dual monostable**: Relationships are measured by both parties; asymmetry is collision
- **RC decay**: Trust is analog, accumulates, and always decays toward zero

The 555 timer, invented in 1971, is the first purpose-built TTL engine. Every timer is a death timer. Every oscillator is a survival signal. The circuit _is_ the philosophy.
