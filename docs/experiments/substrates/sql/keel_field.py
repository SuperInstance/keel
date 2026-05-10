#!/usr/bin/env python3
"""
keel_field.py — SQLite as Coordination Substrate

The field IS the database. Every entity carries its own death.
No central scheduler. No RPC. No message queue.

This module provides the field operations that agents use to:
  1. Register and heartbeat (write heading)
  2. Sense bearings (query other agents' headings)
  3. Detect collisions (converging heading + speed)
  4. Expire stale work (TTL-based reclamation)
  5. Decay trust (provenance-based confidence reduction)
  6. Reclaim dead agent work (drain tiles)

stdlib only: sqlite3, datetime, json, uuid, math
"""

import sqlite3
import datetime
import json
import uuid
import math
import pathlib
import textwrap
import sys


# ===========================================================================
# FIELD INITIALIZATION
# ===========================================================================

def init_field(db_path: str, schema_path: str = None) -> sqlite3.Connection:
    """Initialize a new Keel field database.

    Returns a connection to the field. The field IS the database.
    CREATE TABLE is a keel init.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Concurrent readers/writers
    conn.execute("PRAGMA foreign_keys=ON")

    if schema_path is None:
        schema_path = pathlib.Path(__file__).parent / "schema.sql"

    schema_sql = pathlib.Path(schema_path).read_text()
    conn.executescript(schema_sql)
    conn.commit()
    return conn


# ===========================================================================
# 1. AGENT HEADING: Agent writes its presence and heading to the field
#    INSERT OR REPLACE INTO agents (name, heading, last_heartbeat)
# ===========================================================================

def agent_heartbeat(
    conn: sqlite3.Connection,
    name: str,
    heading: float,
    speed: float = 0.0,
    altitude: float = 0.0,
    role: str = "worker",
    ttl_seconds: int = 300
) -> dict:
    """Agent writes its heading to the field.

    The field doesn't talk TO agents. Agents talk THROUGH the field.
    This is a write — the agent pushing its state into the shared space.
    """
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO agents (name, heading, speed, altitude, role, status, last_heartbeat, ttl_seconds)
        VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            heading = excluded.heading,
            speed = excluded.speed,
            altitude = excluded.altitude,
            role = excluded.role,
            status = 'active',
            last_heartbeat = excluded.last_heartbeat,
            ttl_seconds = excluded.ttl_seconds
    """, (name, heading, speed, altitude, role, now, ttl_seconds))
    conn.commit()
    return {"agent": name, "heading": heading, "heartbeat": now}


# ===========================================================================
# 2. BEARING COMPUTATION: Sense what other agents are doing
#    SELECT a.name, b.name, ABS(a.heading - b.heading) AS angle
# ===========================================================================

def sense_bearings(conn: sqlite3.Connection) -> list:
    """Query all bearing relationships between active agents.

    Returns a list of dicts: agent_a, agent_b, angle_degrees, bearing_rate.
    This IS the field sensing — a SELECT over the shared table.
    """
    cursor = conn.execute("""
        SELECT agent_a, agent_b, angle_degrees, bearing_rate,
               speed_delta, altitude_separation, role_a, role_b
        FROM bearing_view
        ORDER BY angle_degrees ASC
    """)
    return [dict(row) for row in cursor.fetchall()]


def sense_bearings_to(conn: sqlite3.Connection, agent_name: str) -> list:
    """Query bearings for a specific agent — who's near me?"""
    cursor = conn.execute("""
        SELECT agent_a, agent_b, angle_degrees, bearing_rate, speed_delta
        FROM bearing_view
        WHERE agent_a = ? OR agent_b = ?
        ORDER BY angle_degrees ASC
    """, (agent_name, agent_name))
    return [dict(row) for row in cursor.fetchall()]


# ===========================================================================
# 3. COLLISION DETECTION: Find converging agents
#    SELECT * FROM bearing_view WHERE angle < threshold AND rate < threshold
# ===========================================================================

def detect_collisions(
    conn: sqlite3.Connection,
    angle_threshold: float = 15.0,
    rate_threshold: float = 5.0
) -> list:
    """Detect imminent collisions between agents.

    An agent collision is two agents on near-identical headings
    with low bearing rate (meaning they're staying on course toward each other).
    """
    cursor = conn.execute("""
        SELECT agent_a, agent_b, angle_degrees, bearing_rate,
               speed_delta, altitude_separation, collision_risk
        FROM collision_view
        WHERE angle_degrees < ?
          AND bearing_rate < ?
          AND altitude_separation < 10
        ORDER BY collision_risk DESC, angle_degrees ASC
    """, (angle_threshold, rate_threshold))
    return [dict(row) for row in cursor.fetchall()]


# ===========================================================================
# 4. TTL EXPIRY: Death-as-default
#    DELETE FROM tiles WHERE keel_date + ttl < current_timestamp
# ===========================================================================

def reap_stale_tiles(conn: sqlite3.Connection) -> int:
    """Reclaim tiles whose TTL has expired.

    This is death-as-default. Every tile carries its own death.
    The field reclaims it without asking anyone.
    """
    cursor = conn.execute("""
        UPDATE tiles SET state = 'expired', owner = NULL
        WHERE state != 'done'
          AND state != 'expired'
          AND datetime(keel_date, '+' || ttl_seconds || ' seconds') < datetime('now')
    """)
    conn.commit()
    return cursor.rowcount


def reap_dead_agents(conn: sqlite3.Connection) -> list:
    """Mark agents as dead if their heartbeat TTL expired.

    Returns list of dead agent names.
    """
    # Find and mark dead agents
    cursor = conn.execute("""
        UPDATE agents SET status = 'dead'
        WHERE status = 'active'
          AND datetime(last_heartbeat, '+' || ttl_seconds || ' seconds') < datetime('now')
    """)
    dead_count = cursor.rowcount
    conn.commit()

    # Trigger drains tiles from dead agents back to the pool
    cursor = conn.execute("""
        SELECT name FROM agents WHERE status = 'dead'
    """)
    dead_agents = [row["name"] for row in cursor.fetchall()]

    if dead_agents:
        # Drain their tiles
        placeholders = ",".join("?" for _ in dead_agents)
        conn.execute(f"""
            UPDATE tiles SET owner = NULL, state = 'open'
            WHERE owner IN ({placeholders})
              AND state IN ('claimed', 'in_progress')
        """, dead_agents)
        conn.commit()

    return dead_agents


# ===========================================================================
# 5. TRUST DECAY: Provenance-based confidence reduction
#    UPDATE trust SET confidence = confidence * 0.5 WHERE provenance_depth > 0
# ===========================================================================

def decay_trust(conn: sqlite3.Connection, factor: float = 0.5) -> int:
    """Decay trust confidence based on provenance depth.

    Direct trust (depth=0) is strongest.
    Second-hand trust (depth=1) decays by factor.
    Third-hand (depth=2) decays by factor^2.
    Each layer of hearsay reduces confidence.
    """
    cursor = conn.execute("""
        UPDATE trust
        SET confidence = confidence * POWER(?, provenance_depth),
            last_updated = datetime('now')
        WHERE provenance_depth > 0
    """, (factor,))
    conn.commit()
    return cursor.rowcount


def record_trust(
    conn: sqlite3.Connection,
    from_agent: str,
    to_agent: str,
    confidence: float,
    provenance_depth: int = 0,
    ttl_seconds: int = 3600
) -> dict:
    """Record or update a trust relationship."""
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO trust (from_agent, to_agent, confidence, provenance_depth,
                          interactions, last_updated, ttl_seconds)
        VALUES (?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(from_agent, to_agent, provenance_depth) DO UPDATE SET
            confidence = excluded.confidence,
            interactions = interactions + 1,
            last_updated = excluded.last_updated
    """, (from_agent, to_agent, confidence, provenance_depth, now, ttl_seconds))
    conn.commit()
    return {"from": from_agent, "to": to_agent, "confidence": confidence, "depth": provenance_depth}


# ===========================================================================
# 6. TILE OPERATIONS: Claiming and completing work through the field
# ===========================================================================

def create_tile(
    conn: sqlite3.Connection,
    tile_type: str = "task",
    data: dict = None,
    priority: int = 5,
    ttl_seconds: int = 600
) -> str:
    """Create a new tile in the field."""
    tile_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO tiles (id, tile_type, data, priority, keel_date, ttl_seconds)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (tile_id, tile_type, json.dumps(data or {}), priority, now, ttl_seconds))
    conn.commit()
    return tile_id


def claim_tile(conn: sqlite3.Connection, agent_name: str, tile_type: str = None) -> str:
    """Agent claims the highest-priority open tile."""
    if tile_type:
        cursor = conn.execute("""
            SELECT id FROM tiles
            WHERE state = 'open' AND tile_type = ?
            ORDER BY priority DESC, keel_date ASC
            LIMIT 1
        """, (tile_type,))
    else:
        cursor = conn.execute("""
            SELECT id FROM tiles
            WHERE state = 'open'
            ORDER BY priority DESC, keel_date ASC
            LIMIT 1
        """)

    row = cursor.fetchone()
    if row is None:
        return None

    tile_id = row["id"]
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        UPDATE tiles SET owner = ?, state = 'claimed', keel_date = ?
        WHERE id = ? AND state = 'open'
    """, (agent_name, now, tile_id))
    conn.commit()

    # Check if we actually got it (race condition guard)
    cursor = conn.execute("SELECT state FROM tiles WHERE id = ?", (tile_id,))
    result = cursor.fetchone()
    if result and result["state"] == "claimed":
        return tile_id
    return None


def complete_tile(conn: sqlite3.Connection, tile_id: str, agent_name: str, result: dict = None) -> bool:
    """Agent marks a tile as done."""
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.execute("""
        UPDATE tiles SET state = 'done', completed_at = ?, data = ?
        WHERE id = ? AND owner = ?
    """, (now, json.dumps(result or {}), tile_id, agent_name))
    conn.commit()
    return cursor.rowcount > 0


# ===========================================================================
# 7. FIELD INSPECTION: See what's on the field
# ===========================================================================

def field_status(conn: sqlite3.Connection) -> dict:
    """Get a snapshot of the entire field state."""
    result = {}

    cursor = conn.execute("SELECT COUNT(*) as c FROM agents WHERE status = 'active'")
    result["active_agents"] = cursor.fetchone()["c"]

    cursor = conn.execute("SELECT COUNT(*) as c FROM agents WHERE status = 'dead'")
    result["dead_agents"] = cursor.fetchone()["c"]

    for state in ('open', 'claimed', 'in_progress', 'done', 'expired'):
        cursor = conn.execute("SELECT COUNT(*) as c FROM tiles WHERE state = ?", (state,))
        result[f"tiles_{state}"] = cursor.fetchone()["c"]

    cursor = conn.execute("""
        SELECT COUNT(*) as c FROM stale_tiles_view
    """)
    result["stale_tiles"] = cursor.fetchone()["c"]

    cursor = conn.execute("""
        SELECT COUNT(*) as c FROM dead_agents_view
    """)
    result["agents_pending_death"] = cursor.fetchone()["c"]

    cursor = conn.execute("SELECT COUNT(*) as c FROM trust")
    result["trust_relationships"] = cursor.fetchone()["c"]

    return result


# ===========================================================================
# 8. MAINTAIN: Run the field's natural processes
# ===========================================================================

def tick(conn: sqlite3.Connection) -> dict:
    """Run one full field tick: reap dead agents, stale tiles, decay trust.

    Returns: dict of what happened
    """
    dead_agents = reap_dead_agents(conn)
    stale_count = reap_stale_tiles(conn)
    trust_count = decay_trust(conn)

    return {
        "dead_agents": dead_agents,
        "stale_tiles_reaped": stale_count,
        "trust_entries_decayed": trust_count,
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }


# ===========================================================================
# MAIN: Simple CLI for field operations
# ===========================================================================

def _print_field(conn: sqlite3.Connection):
    """Pretty-print the field state."""
    status = field_status(conn)
    print("\n=== FIELD STATUS ===")
    print(f"  Active agents:  {status['active_agents']}")
    print(f"  Dead agents:    {status['dead_agents']}")
    print(f"  Open tiles:     {status['tiles_open']}")
    print(f"  Claimed tiles:  {status['tiles_claimed']}")
    print(f"  Done tiles:     {status['tiles_done']}")
    print(f"  Expired tiles:  {status['tiles_expired']}")
    print(f"  Stale tiles:    {status['stale_tiles']}")
    print(f"  Pending death:  {status['agents_pending_death']}")
    print(f"  Trust count:    {status['trust_relationships']}")

    bearings = sense_bearings(conn)
    if bearings:
        print(f"\n=== BEARINGS ({len(bearings)} pairs) ===")
        for b in bearings:
            print(f"  {b['agent_a']} <-> {b['agent_b']}: {b['angle_degrees']:.1f}° "
                  f"(rate={b['bearing_rate']:.2f}, {b['role_a']}/{b['role_b']})")

    collisions = detect_collisions(conn)
    if collisions:
        print(f"\n=== COLLISIONS ({len(collisions)}) ===")
        for c in collisions:
            print(f"  ⚠ {c['agent_a']} <-> {c['agent_b']}: {c['collision_risk']} "
                  f"(angle={c['angle_degrees']:.1f}°, rate={c['bearing_rate']:.2f})")


def main():
    """Simple CLI: `keel_field.py <db_path> [command]`"""
    if len(sys.argv) < 3:
        print("Usage: keel_field.py <db_path> <command> [args...]")
        print("Commands:")
        print("  init                      Initialize the field")
        print("  heartbeat <name> <heading> [speed] [altitude] [role] [ttl]")
        print("  bearings                  Show all bearings")
        print("  collisions [angle] [rate] Show collisions")
        print("  tick                      Run one field tick")
        print("  status                   Show field status")
        print("  create_tile <type> <data_json> [priority] [ttl]")
        print("  claim <agent> [type]      Claim a tile")
        print("  complete <tile_id> <agent> [result_json]")
        print("  record_trust <from> <to> <confidence> [depth]")
        sys.exit(1)

    db_path = sys.argv[1]
    command = sys.argv[2]
    args = sys.argv[3:]

    conn = init_field(db_path)

    if command == "init":
        _print_field(conn)
    elif command == "heartbeat":
        name = args[0]
        heading = float(args[1])
        speed = float(args[2]) if len(args) > 2 else 0.0
        altitude = float(args[3]) if len(args) > 3 else 0.0
        role = args[4] if len(args) > 4 else "worker"
        ttl = int(args[5]) if len(args) > 5 else 300
        result = agent_heartbeat(conn, name, heading, speed, altitude, role, ttl)
        print(f"  Heartbeat: {result}")
        _print_field(conn)
    elif command == "bearings":
        bearings = sense_bearings(conn)
        for b in bearings:
            print(f"  {b['agent_a']} <-> {b['agent_b']}: {b['angle_degrees']:.1f}° "
                  f"(rate={b['bearing_rate']:.2f}, sep={b['altitude_separation']})")
    elif command == "collisions":
        angle_threshold = float(args[0]) if args else 15.0
        rate_threshold = float(args[1]) if len(args) > 1 else 5.0
        collisions = detect_collisions(conn, angle_threshold, rate_threshold)
        for c in collisions:
            print(f"  ⚠ {c['agent_a']} <-> {c['agent_b']}: {c['collision_risk']} ({c['angle_degrees']:.1f}°)")
        if not collisions:
            print("  No collisions detected.")
    elif command == "tick":
        result = tick(conn)
        print(f"  Tick: {result}")
        _print_field(conn)
    elif command == "status":
        _print_field(conn)
    elif command == "create_tile":
        tile_type = args[0]
        data = json.loads(args[1]) if len(args) > 1 else {}
        priority = int(args[2]) if len(args) > 2 else 5
        ttl = int(args[3]) if len(args) > 3 else 600
        tile_id = create_tile(conn, tile_type, data, priority, ttl)
        print(f"  Created tile: {tile_id}")
    elif command == "claim":
        agent = args[0]
        tile_type = args[1] if len(args) > 1 else None
        tile_id = claim_tile(conn, agent, tile_type)
        if tile_id:
            print(f"  {agent} claimed tile: {tile_id}")
        else:
            print(f"  No available tiles for {agent}")
    elif command == "complete":
        tile_id = args[0]
        agent = args[1]
        result = json.loads(args[2]) if len(args) > 2 else {}
        success = complete_tile(conn, tile_id, agent, result)
        print(f"  Tile {tile_id} {'completed' if success else 'FAILED'}")
    elif command == "record_trust":
        from_agent, to_agent = args[0], args[1]
        confidence = float(args[2])
        depth = int(args[3]) if len(args) > 3 else 0
        result = record_trust(conn, from_agent, to_agent, confidence, depth)
        print(f"  Trust: {result}")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

    conn.close()


if __name__ == "__main__":
    main()
