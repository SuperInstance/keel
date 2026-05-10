#!/usr/bin/env python3
"""
demo.py — SQLite as Coordination Substrate

Three agents coordinate through the shared field (a single SQLite file).
No RPC. No messages. No service discovery. Just SQL reads and writes.

Agents:
  - SCOUT (heading=045°, speed=10) — fast scout exploring
  - WORKER (heading=050°, speed=5) — slower worker following near the scout
  - COORDINATOR (heading=200°, speed=3) — heading opposite direction

The field senses the convergence between scout and worker,
detects the collision risk, and agents self-correct.
"""

import sqlite3
import time
import os
import sys

# Add parent dir to path for keel_field import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from keel_field import (
    init_field, agent_heartbeat, sense_bearings, sense_bearings_to,
    detect_collisions, create_tile, claim_tile, complete_tile,
    record_trust, decay_trust, tick, field_status, _print_field
)

DB_PATH = "/tmp/keel-field-demo.db"

# Clean up from previous runs
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

# ===========================================================================
# SCENE 1: Agents write their headings to the field
# ===========================================================================
print("=" * 60)
print("KEEL TTL ENGINE — SQLite Coordination Substrate Demo")
print("=" * 60)
print("The field IS the database. No RPC. No messages. No scheduler.")
print("Agents coordinate through shared SQL tables.")
print()

conn = init_field(DB_PATH)
print("[INIT] Field initialized at /tmp/keel-field-demo.db")
print()

# --------------------------------------------------------------------------
# SCENE 2: Three agents register themselves
# Each one writes its heading to the agents table.
# The field knows nothing except what agents write.
# --------------------------------------------------------------------------
print(">>> SCENE 1: Agents register on the field")
print("    (Each agent writes heading/speed/altitude to the agents table)")
print()

scout = agent_heartbeat(conn, "scout-alpha", heading=45.0, speed=10.0,
                        altitude=50.0, role="scout", ttl_seconds=60)
print(f"  🔭 scout-alpha: heading=045° speed=10 alt=50  [WRITTEN TO agents TABLE]")

worker = agent_heartbeat(conn, "worker-beta", heading=50.0, speed=5.0,
                         altitude=45.0, role="worker", ttl_seconds=120)
print(f"  🛠  worker-beta:  heading=050° speed=5  alt=45  [WRITTEN TO agents TABLE]")

coordinator = agent_heartbeat(conn, "coordinator-gamma", heading=200.0,
                              speed=3.0, altitude=100.0, role="coordinator",
                              ttl_seconds=180)
print(f"  📡 coordinator-gamma: heading=200° speed=3 alt=100 [WRITTEN TO agents TABLE]")

print()
print(f"  → Query: SELECT * FROM agents WHERE status='active'")
cursor = conn.execute("SELECT name, heading, speed, role FROM agents WHERE status='active'")
for row in cursor.fetchall():
    print(f"    {dict(row)}")

print()

# --------------------------------------------------------------------------
# SCENE 3: Bearing sensing — agents query the field
# Any agent can SELECT to see what others are doing.
# The bearing_view computes angles between all agent pairs.
# --------------------------------------------------------------------------
print(">>> SCENE 2: Bearing sensing (agents query the field)")
print("    (SELECT from bearing_view — angles between all agent pairs)")
print()

bearings = sense_bearings(conn)
for b in bearings:
    print(f"  📐 {b['agent_a']} ↔ {b['agent_b']}: "
          f"angle={b['angle_degrees']:.1f}°  rate={b['bearing_rate']:.2f}  "
          f"roles: {b['role_a']}/{b['role_b']}")

print()
print(f"  → Query: SELECT * FROM bearing_view ORDER BY angle_degrees ASC")
cursor = conn.execute("SELECT agent_a, agent_b, ROUND(angle_degrees,1) as angle, "
                      "ROUND(bearing_rate,3) as rate FROM bearing_view")
for row in cursor.fetchall():
    print(f"    {dict(row)}")

print()

# --------------------------------------------------------------------------
# SCENE 4: Collision detection
# Scout and worker are on near-identical headings (45° vs 50° = 5° apart)
# with scout moving fast (10) and worker slower (5).
# The field detects this as a converging pair.
# --------------------------------------------------------------------------
print(">>> SCENE 3: Collision detection")
print("    scout-alpha (045° speed=10) and worker-beta (050° speed=5) are converging")
print()

collisions = detect_collisions(conn, angle_threshold=20.0, rate_threshold=10.0)
for c in collisions:
    print(f"  ⚠️  COLLISION RISK: {c['agent_a']} <-> {c['agent_b']}")
    print(f"     Angle: {c['angle_degrees']:.1f}°  Rate: {c['bearing_rate']:.2f}")
    print(f"     Risk:  {c['collision_risk']}")

print()
print(f"  → Query: SELECT * FROM collision_view WHERE angle_degrees < 20 AND bearing_rate < 10")
cursor = conn.execute("""
    SELECT agent_a, agent_b, ROUND(angle_degrees,1) as angle,
           ROUND(bearing_rate,3) as rate, collision_risk
    FROM collision_view WHERE angle_degrees < 20 AND bearing_rate < 10
""")
for row in cursor.fetchall():
    print(f"    {dict(row)}")

print()

# --------------------------------------------------------------------------
# SCENE 5: Agents self-correct based on field sensing
# The scout sees the collision risk and adjusts heading.
# In a real system, the agent would read the field and act.
# Here we simulate: scout adjusts heading to 080° to diverge.
# --------------------------------------------------------------------------
print(">>> SCENE 4: Agent self-correction")
print("    scout-alpha SENSES the collision risk and adjusts heading")
print()

# Scout reads its bearings
scout_bearings = sense_bearings_to(conn, "scout-alpha")
for b in scout_bearings:
    other = b['agent_b'] if b['agent_a'] == 'scout-alpha' else b['agent_a']
    print(f"    scout-alpha sees: {other} at {b['angle_degrees']:.1f}°")

# Scout changes heading to diverge
print()
print("    Action: scout-alpha changes heading from 045° → 080° (diverges from worker)")
agent_heartbeat(conn, "scout-alpha", heading=80.0, speed=10.0,
                altitude=50.0, role="scout", ttl_seconds=60)

# Re-check bearings
bearings = sense_bearings(conn)
print()
print("    After correction:")
for b in bearings:
    if b['agent_a'] == 'scout-alpha' or b['agent_b'] == 'scout-alpha':
        print(f"    📐 {b['agent_a']} ↔ {b['agent_b']}: "
              f"angle={b['angle_degrees']:.1f}° now "
              f"(was 5°, now {b['angle_degrees']:.1f}° — collision avoided)")

print()

# --------------------------------------------------------------------------
# SCENE 6: Work via tiles — claiming and completing through the field
# The coordinator creates tiles. Workers claim them.
# All coordination is through the tiles table.
# --------------------------------------------------------------------------
print(">>> SCENE 5: Work coordination through the field")
print("    coordinator-gamma creates tiles. scout-alpha claims them.")
print("    All coordination is through the tiles TABLE — no messages.")
print()

# Coordinator creates tiles
tile1 = create_tile(conn, tile_type="survey", data={"zone": "north-ridge"},
                    priority=8, ttl_seconds=120)
print(f"  📋 Created tile: {tile1[:8]}... (type=survey, priority=8)")

tile2 = create_tile(conn, tile_type="survey", data={"zone": "east-ridge"},
                    priority=6, ttl_seconds=120)
print(f"  📋 Created tile: {tile2[:8]}... (type=survey, priority=6)")

tile3 = create_tile(conn, tile_type="cargo", data={"item": "supplies"},
                    priority=5, ttl_seconds=120)
print(f"  📋 Created tile: {tile3[:8]}... (type=cargo, priority=5)")

print()

# Scout claims the highest-priority tile (survey, zone=north-ridge)
print("    scout-alpha queries: SELECT id FROM tiles WHERE state='open' ORDER BY priority DESC")
claimed = claim_tile(conn, "scout-alpha", tile_type="survey")
print(f"    scout-alpha claimed: {claimed[:8]}... (highest priority survey tile)")
print()

# Worker also claims a tile
claimed2 = claim_tile(conn, "worker-beta")
print(f"    worker-beta claimed: {claimed2[:8]}... (next available tile)")

# Complete the work through the field
complete_tile(conn, claimed, "scout-alpha", result={"zones_surveyed": 3, "quality": 0.95})
print(f"    scout-alpha completed: {claimed[:8]}... ↔ status='done' written to tiles table")

complete_tile(conn, claimed2, "worker-beta", result={"items": 5, "status": "full"})
print(f"    worker-beta completed: {claimed2[:8]}... ↔ status='done' written to tiles table")

print()

# --------------------------------------------------------------------------
# SCENE 7: Trust — recording and decaying through the field
# Agents record trust via INSERT/UPDATE on the trust TABLE.
# Trust decays via UPDATE WHERE provenance_depth > 0.
# --------------------------------------------------------------------------
print(">>> SCENE 6: Trust through the field")
print("    Trust is stored in the trust TABLE. Confidence decays with provenance.")
print()

record_trust(conn, "scout-alpha", "worker-beta", confidence=0.95,
             provenance_depth=0, ttl_seconds=3600)
print(f"  direct trust: scout-alpha → worker-beta (confidence=0.95, depth=0)")

record_trust(conn, "worker-beta", "coordinator-gamma", confidence=0.85,
             provenance_depth=0, ttl_seconds=3600)
print(f"  direct trust: worker-beta → coordinator-gamma (confidence=0.85, depth=0)")

# Second-hand trust: scout trusts coordinator via worker's word
record_trust(conn, "scout-alpha", "coordinator-gamma", confidence=0.75,
             provenance_depth=1, ttl_seconds=3600)
print(f"  hearsay trust: scout-alpha → coordinator-gamma (confidence=0.75, depth=1)")
print(f"    (scout never worked with coordinator directly — hearsay via worker)")

print()
print(f"  → Query: SELECT * FROM trust")
cursor = conn.execute("SELECT from_agent, to_agent, confidence, provenance_depth "
                      "FROM trust")
for row in cursor.fetchall():
    print(f"    {dict(row)}")

print()

# Apply trust decay
print(f"  Tick: decaying trust by 0.5^provenance_depth...")
count = decay_trust(conn, factor=0.5)
print(f"  {count} trust entries decayed")

cursor = conn.execute("SELECT from_agent, to_agent, confidence, provenance_depth "
                      "FROM trust")
for row in cursor.fetchall():
    print(f"    {dict(row)}")
print(f"    → Note: depth=0 trust unchanged (0.95, 0.85 remain)")
print(f"    → depth=1 trust halved (0.75 → 0.375)")

print()

# --------------------------------------------------------------------------
# SCENE 8: Death as default — TTL reclamation
# We simulate time passing by creating tiles with very short TTLs.
# Then the field reclaims them.
# --------------------------------------------------------------------------
print(">>> SCENE 7: TTL expiry — death as default")
print("    Every entity carries its own death. No central scheduler.")
print()

# Create tiles with 1-second TTL
short_tile = create_tile(conn, tile_type="ephemeral", data={"temp": "data"},
                         priority=1, ttl_seconds=1)
print(f"  Created ephemeral tile (TTL=1s): {short_tile[:8]}...")

# They exist now
cursor = conn.execute("SELECT id, state FROM tiles WHERE id = ?", (short_tile,))
row = cursor.fetchone()
print(f"  Before expiry: tile {row['id'][:8]}... state={row['state']}")

# Wait for TTL
print(f"  Waiting 2.5s for TTL expiry...")
time.sleep(2.5)

# Tick the field — TTL reclamation
result = tick(conn)
reaped = result['stale_tiles_reaped']
print(f"  Tick result: stale_tiles_reaped={reaped}")

cursor = conn.execute("SELECT id, state FROM tiles WHERE id = ?", (short_tile,))
row = cursor.fetchone()
state_label = "✅ expired — reclaimed by field" if row['state'] == 'expired' else f"still {row['state']} (reap returned {reaped})"
print(f"  After expiry:  tile {row['id'][:8]}... state={row['state']} ({state_label})")
print()

# --------------------------------------------------------------------------
# SCENE 9: Full field snapshot
# --------------------------------------------------------------------------
print(">>> SCENE 8: Final field state")
print()

status = field_status(conn)
for key, value in status.items():
    print(f"  {key}: {value}")

print()
print("=" * 60)
print("DEMO COMPLETE")
print("=" * 60)
print()
print("Key insight: SQL IS the coordination protocol.")
print()
print("  CREATE TABLE      = keel init")
print("  INSERT/REPLACE    = writing heading to the field")
print("  SELECT ... JOIN   = bearing-rate sensing")
print("  DELETE WHERE ttl  = death as default")
print("  UPDATE confidence = trust decay")
print()
print("No RPC. No messages. No service discovery.")
print("One database file. The field IS the data.")
print()

conn.close()
