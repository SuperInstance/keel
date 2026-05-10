# Keel TTL-Native CPU — Register-Transfer Level Design

## Core Philosophy

"Death is default. The field is the command."

A Keel CPU does not execute a `KILL` instruction. It doesn't need one. Every datum carries its own termination timer. When the timer reaches zero, the datum dies automatically. The CPU is the field — it observes and routes signal, it does not impose death.

## Architecture Overview

```
+------------------------------------------------------------+
|                    KEEL TTL CPU                             |
|  +------------------+    +------------------+               |
|  |   TTL Register   |    |   Data Register  |               |
|  |   File (×32)     |    |   File (×32)     |               |
|  |   8-bit counters |    |   8-bit words    |               |
|  |   (256 max)      |    |   (256 vals)     |               |
|  +------------------+    +------------------+               |
|          |                        |                          |
|          v                        v                          |
|  +------------------+    +------------------+               |
|  | TTL Comparator   |    |   ALU (8-bit)    |               |
|  | (> 0 → alive)    |    |   ADD, SUB, AND, |               |
|  | (= 0 → stale)    |    |   OR, XOR, SHL   |               |
|  +------------------+    +------------------+               |
|          |                        |                          |
|          +----------+-------------+                          |
|                     |                                        |
|                     v                                        |
|  +-------------------------------------------+              |
|  |   Tristate Bus Interface                  |              |
|  |   (enabled when TTL > 0)                  |              |
|  +-------------------------------------------+              |
|                     |                                        |
|                     v                                        |
|  +-------------------------------------------+              |
|  |   Death Interrupt Controller              |              |
|  |   (fires on any TTL=0 register read)      |              |
|  +-------------------------------------------+              |
+------------------------------------------------------------+
```

## Register File

### Data Register Structure (32 registers × 8 bits)

```
 7     6     5     4     3     2     1     0
+-----+-----+-----+-----+-----+-----+-----+-----+
|                  Data Value (V)                 |
+-----+-----+-----+-----+-----+-----+-----+-----+
```

### TTL Register File (32 registers × 8 bits, paired 1:1 with data)

```
 7     6     5     4     3     2     1     0
+-----+-----+-----+-----+-----+-----+-----+-----+
|              TTL Counter Value (C)              |
+-----+-----+-----+-----+-----+-----+-----+-----+
```

### Stale Flag (1 bit per register, stored separately)

```
+---+---+
| S | ... (32 bits total, one per register)
+---+---+
```

- S = 0: TTL > 0, data is valid
- S = 1: TTL = 0, data is stale (dead)

## Microarchitecture

### TTL Decrement Logic

Every clock cycle, all TTL registers decrement by 1 (configurable decrement amount via microcode):

```
∀ r ∈ [0..31]:
  if TTL[r] > 0:
    TTL[r] ← TTL[r] - 1
    Stale[r] ← 0
  else:
    TTL[r] ← 0
    Stale[r] ← 1
```

The decrement is parallel — all TTL counters tick down simultaneously. This is the "heartbeat" of the system: the passage of time IS the decrement operation.

### Register Read (with Death Detection)

```
func read(reg_id):
  if TTL[reg_id] > 0:
    Stale[reg_id] ← 0  // acknowledge freshness
    return Data[reg_id]
  else:
    Stale[reg_id] ← 1
    DEATH_INTERRUPT ← reg_id  // fire death interrupt with source
    return Hi-Z  // bus goes high-impedance
```

Reading stale data is NOT silent corruption — it asserts the ERROR line. The CPU doesn't prevent reading dead data, but it surfaces it honestly.

### Register Write (Life Granting)

```
func write(reg_id, value, ttl_value):
  Data[reg_id] ← value
  TTL[reg_id] ← ttl_value
  Stale[reg_id] ← 0
```

Writing to a register RESETS its TTL. This is the data-plane equivalent of revival — a new value carries new life. This is NOT a `KILL` instruction; it's a natural consequence of the architecture.

## Instruction Set

### Data Instructions

| Mnemonic | Opcode | Format | Description |
|----------|--------|--------|-------------|
| LOAD Rd, addr | 0000 | LOAD Rd, [addr] | Load from memory, set TTL to max |
| STORE Rs, addr | 0001 | STORE Rs, [addr] | Store to memory (TTL not transferred) |
| MOV Rd, Rs | 0010 | MOV Rd, Rs | Copy Rs → Rd (TTL: min(TTL[Rs], TTL[Rd])) |
| ADD Rd, Rs, Rt | 0011 | ADD Rd, Rs, Rt | Rd = Rs + Rt (TTL: min of all sources) |
| SUB Rd, Rs, Rt | 0100 | SUB Rd, Rs, Rt | Rd = Rs - Rt |
| AND Rd, Rs, Rt | 0101 | AND Rd, Rs, Rt | Rd = Rs & Rt |
| OR Rd, Rs, Rt | 0110 | OR Rd, Rs, Rt | Rd = Rs \| Rt |
| XOR Rd, Rs, Rt | 0111 | XOR Rd, Rs, Rt | Rd = Rs ^ Rt |
| SHL Rd, Rs, imm | 1000 | SHL Rd, Rs, N | Rd = Rs << N |

### TTL Instructions

| Mnemonic | Opcode | Format | Description |
|----------|--------|--------|-------------|
| GRANT Rd, Rs | 1001 | GRANT Rd, Rs | Copy Rs's TTL to Rd (life transfer) |
| EXAMINE Rd, Rs | 1010 | EXAMINE Rd, Rs | Read Rs's TTL value into Rd's data |
| EXTEND Rd, N | 1011 | EXTEND Rd, N | Add N to Rd's TTL counter |
| REFRESH Rd | 1100 | REFRESH Rd | Reset Rd's TTL to max (heartbeat) |

GRANT is the data-plane equivalent of `MOV` for TTL — you can transfer remaining life between registers. This is cooperative survival, not imposed death.

### Control Instructions

| Mnemonic | Opcode | Format | Description |
|----------|--------|--------|-------------|
| BNE Rs, Rt, addr | 1101 | BNE | Branch if Rs != Rt |
| BEQ Rs, Rt, addr | 1110 | BEQ | Branch if Rs == Rt |
| HALT | 1111 | HALT | Stop clock (all TTLs freeze) |

### Explicitly ABSENT: KILL

There is no `KILL` instruction. Data dies because its timer runs out, not because an instruction killed it. If you need data to die sooner, you SET a lower TTL when writing it:

```
LOAD R0, [sensor_data]  // load sensor reading
GRANT R1, R0             // use R0's TTL for R1 too
EXTEND R1, 50            // give R1 50 more ticks
```

Natural data lifetime management. No murder instruction needed.

## Interrupt System

### Death Interrupt Vector

| IRQ | Priority | Source | Description |
|-----|----------|--------|-------------|
| 0 | 0 (highest) | TTL Stall | Write to stale register (death on write) |
| 1 | 1 | TTL Read | Read from stale register (death on read) |
| 2 | 2 | TTL Expiry | Timer reached zero (automatic, no operation) |
| 3 | 3 | Error Line | Bus Hi-Z detected by external agent |

### Interrupt Handling Flow

```
1. TTL counter reaches 0 for register R
2. Stale[R] ← 1
3. If next operation reads R:
   a. Data bus goes Hi-Z
   b. Error line asserts
   c. Death interrupt fires with register ID on address lines
4. ISR reads error register, identifies dead register
5. ISR can either:
   a. GRANT fresh TTL to the register (resurrection)
   b. Route around the dead register
   c. Let the system hang (if no handler installed)
```

## Bus Protocol

### Tristate Bus Lines

| Line | Width | Direction | Description |
|------|-------|-----------|-------------|
| D[7:0] | 8 | Bidir | Data bus (Hi-Z when TTL=0) |
| A[4:0] | 5 | Out | Register address |
| R/W | 1 | Out | Read (1) / Write (0) |
| VALID | 1 | Out | Data valid (TTL > 0) |
| ERROR | 1 | In/Out | Stale read detected |
| CLK | 1 | In | System clock |

### Bus Arbitration

Multiple agents on the same bus can read/write. Each agent holds its own set of TTL registers. An agent that has reached TTL=0 on all its registers goes Hi-Z on all lines — it effectively disappears from the bus.

This IS death as circuit behavior: no signal, no state, just an open circuit.

## Physical Implementation (TTL Logic)

### Component Count per Register (8-bit)

| Component | Count | Function |
|-----------|-------|----------|
| 74LS161 (4-bit counter) | 2 | 8-bit TTL counter (cascaded) |
| 74LS374 (octal flip-flop) | 1 | Data register storage |
| 74LS85 (4-bit comparator) | 2 | Check if TTL > 0 (cascaded) |
| 74LS125 (tristate buffer) | 8 | Bus output (enabled by TTL>0) |
| 74LS08 (AND gate) | 1 | Enable logic (TTL>0 AND read/write) |
| 74LS32 (OR gate) | 1 | Error line aggregation |
| 74LS04 (inverter) | 2 | Stale flag logic |

### Total for 32-Register CPU

| Component | Count | Per Unit | Total |
|-----------|-------|----------|-------|
| 74LS161 | 64 | $0.50 | $32.00 |
| 74LS374 | 32 | $0.80 | $25.60 |
| 74LS85 | 64 | $0.50 | $32.00 |
| 74LS125 | 256 | $0.30 | $76.80 |
| 74LS08 | 32 | $0.20 | $6.40 |
| 74LS32 | 32 | $0.20 | $6.40 |
| 74LS04 | 64 | $0.15 | $9.60 |
| Clock gen | 1 | $0.50 | $0.50 |
| PCB | 1 | $5.00 | $5.00 |
| **Total** | | | **~$194.30** |

This is buildable TODAY on a breadboard for under $200.

## Key Insight

The TTL CPU doesn't need software to manage lifetimes. The hardware IS the lifetime manager. Every clock tick is a heartbeat, every register carry is a birth, every TTL expiry is a death. The CPU is the stage; life and death are the actors.
