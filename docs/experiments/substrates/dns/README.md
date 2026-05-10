# 🔮 Keel TTL Engine — DNS Edition

```
DNS invented TTL in 1987 (RFC 1035).
Every DNS record is a Keel tile.
The resolver IS the field.
NXDOMAIN is death.
The entire Keel architecture was running in every DNS resolver
on the internet, long before Keel existed.
We just discovered what it was.
```

## The Mapping

| Keel Concept     | DNS Equivalent       | Mechanism                               |
|-------------------|----------------------|------------------------------------------|
| Agent presence    | A record             | Record exists = alive                    |
| Agent death       | NXDOMAIN             | Record doesn't exist = gone              |
| Self-termination  | TTL field            | "I exist for N seconds, then I die"      |
| First-person      | Per-record TTL       | Each record carries its own death timer  |
| Heading           | TXT record           | Vector directional data                  |
| Bearing           | TXT record on subdomain | One agent's observation of another    |
| Trust             | TXT record           | Confidence assertions, slow-changing     |
| Heartbeat         | Zone update          | Re-write records before TTL expiry       |
| The field         | DNS resolver cache   | Automatically drops expired records      |
| No re-query       | Cache semantics      | Resolver waits; old data disappears      |
| Bearing sensor    | `dig` command        | Query IS measurement                     |

## The Core Insight: TTL Was Already Keel

Keel says: **"Death is default. The field is the command. Every tile carries its own TTL."**

DNS says:
- Every resource record **has a TTL field**. It is mandatory.
- The TTL says how many seconds the record is valid.
- The resolver **does not decide** when to delete the record.
- The record **already knows** when it will die. It was told at birth.
- After TTL expires, the resolver naturally drops it.
- No one polls. No one checks. The record simply ceases to exist.

This is **first-person self-termination**, exactly as Keel defines it.

**DNS invented first-person death in 1987.**

A DNS resolver does not ask "Is agent-01 still alive?" It asks "What is agent-01's A record?" If the record's TTL hasn't expired, the resolver uses the cached value. If it has expired, the resolver queries again. If there is no record (NXDOMAIN), then the agent is dead.

The resolver **never decides to kill anything**. The record decides when it dies. The resolver merely carries out the sentence.

## The Protocol Stack

```
┌─────────────────────────────────────┐
│  APPLICATION                         │
│  dig agent-01.fleet.example A        │
├─────────────────────────────────────┤
│  DNS RESOLVER (the field)            │
│  Checks cache:                       │
│    - Record exists + TTL valid = ✓   │
│    - Record exists + TTL expired = ✗ │
│    - No record = NXDOMAIN (DEAD)     │
├─────────────────────────────────────┤
│  AUTHORITATIVE SERVER                │
│  Serves zone records with TTL        │
│  Does NOT track liveness             │
│  "I just serve what the zone says"   │
├─────────────────────────────────────┤
│  AGENT (keel-dns-agent.sh)           │
│  Updates zone records periodically   │
│  Stop updating = TTL expires = DEAD  │
│  dig = bearing-rate sensor           │
└─────────────────────────────────────┘
```

## Why This Is Important

DNS is the **most deployed TTL protocol on Earth**. Every internet user runs a DNS resolver. Every DNS response includes a TTL. The protocol already does what Keel was designed to do.

**Mapping Keel onto DNS does two things:**

1. **Proves the architecture is sound.** If it maps cleanly onto DNS, it's not an invention — it's a discovery of a pattern that already exists.

2. **Shows the limits.** DNS TTL is coarse (whole seconds), DNS updates are manual (zone transfers), and DNS doesn't naturally express rates or vectors. These are real constraints, but they're not fundamental — they're DNS-specific implementations of a deeper TTL-first pattern.

## Running the Demo

```bash
# Terminal 1: Start the DNS server
python3 keel-dns-server.py --port 5353 --demo

# Terminal 2: Start an agent
chmod +x keel-dns-agent.sh
./keel-dns-agent.sh agent-01 /tmp/keel.db 5353

# Terminal 3: Query like the field does
dig @127.0.0.1 -p 5353 agent-01.fleet.example A
dig @127.0.0.1 -p 5353 agent-01.fleet.example TXT
dig @127.0.0.1 -p 5353 bearing.agent-01.agent-02.fleet.example TXT
dig @127.0.0.1 -p 5353 trust.agent-01.fleet.example TXT
```

## The Proof

**Before Keel existed, DNS already had Keel.**

Every DNS record carries its death in its TTL field. Every DNS resolver is a field that naturally forgets expired records. NXDOMAIN is the protocol's death signal — the record doesn't exist, and the resolver knows it without being told "this agent is dead."

The Keel architecture is not novel. It is DNS rediscovered from first principles.

**What IS novel**: Realizing that DNS is not just a name service. It's a **distributed first-person death protocol** with 40 years of battle testing, used by every computer on the internet, operating at scale no other death protocol has ever approached.

## Files in This Model

| File | Description |
|------|-------------|
| `keel-dns-schema.txt` | Zone file format spec for Keel records |
| `keel-dns-server.py` | Minimal authoritative DNS server |
| `keel-dns-agent.sh` | Shell agent that publishes presence, heading, bearings |
| `README.md` | This file |

## The Final Insight

DNS doesn't need Keel. **DNS IS Keel.** It was Keel before anyone named it.

What we call "first-person self-termination" is what a DNS resolver has always done with TTL. What we call "the field is the command" is a resolver cache. What we call "death is default" is NXDOMAIN.

The entire Keel architecture was there in 1987, running on the internet we built.

We didn't invent it. We discovered we were describing it.
