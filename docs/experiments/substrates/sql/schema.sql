-- ============================================================================
-- schema.sql — Keel TTL Engine: SQLite as Coordination Substrate
--
-- The field IS the database. Every entity carries its own death.
-- No central scheduler. No RPC. No message queue.
-- CREATE TABLE is a keel init.
-- SELECT is bearing-rate sensing.
-- DELETE WHERE ttl_expired is death-as-default.
-- ============================================================================

-- --------------------------------------------------------------------------
-- KEEL TABLE: agents
-- Every agent registers itself by writing its heading and heartbeat.
-- The field doesn't talk TO agents. Agents talk THROUGH the field.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agents (
    name            TEXT PRIMARY KEY,           -- Agent identity (unique)
    heading         REAL NOT NULL DEFAULT 0.0,  -- Current heading in degrees [0, 360)
    speed           REAL NOT NULL DEFAULT 0.0,  -- Current speed (units/tick)
    altitude        REAL NOT NULL DEFAULT 0.0,  -- Altitude/layer (for 3D separation)
    role            TEXT NOT NULL DEFAULT 'worker',  -- scout | worker | coordinator
    status          TEXT NOT NULL DEFAULT 'active',   -- active | paused | draining | dead
    last_heartbeat  TEXT NOT NULL DEFAULT (datetime('now')),  -- Last contact
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    ttl_seconds     INTEGER NOT NULL DEFAULT 300,  -- Self-termination TTL
    metadata        TEXT DEFAULT '{}'             -- JSON blob for extension
);

-- --------------------------------------------------------------------------
-- KEEL TABLE: tiles
-- Tiles are units of work. Each tile carries its own expiry.
-- No central scheduler deletes them — the field does.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tiles (
    id              TEXT PRIMARY KEY,             -- Tile UUID
    tile_type       TEXT NOT NULL DEFAULT 'task', -- task | resource | waypoint
    owner           TEXT,                         -- Agent currently working it (NULL = free)
    data            TEXT NOT NULL DEFAULT '{}',   -- Tile payload as JSON
    priority        INTEGER NOT NULL DEFAULT 5,   -- 1-10 priority
    state           TEXT NOT NULL DEFAULT 'open',  -- open | claimed | in_progress | done | expired
    keel_date       TEXT NOT NULL DEFAULT (datetime('now')),  -- Birth of the tile
    ttl_seconds     INTEGER NOT NULL DEFAULT 600,  -- Tile dies after this many seconds
    completed_at    TEXT                          -- When the tile was finished
);

-- --------------------------------------------------------------------------
-- KEEL TABLE: tasks
-- Tasks are explicit work assignments with their own TTL.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT DEFAULT '',
    assignee        TEXT REFERENCES agents(name),
    priority        INTEGER NOT NULL DEFAULT 5,
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending | assigned | active | done | expired
    keel_date       TEXT NOT NULL DEFAULT (datetime('now')),
    deadline        TEXT,                          -- Optional hard deadline
    ttl_seconds     INTEGER NOT NULL DEFAULT 3600, -- Task expires after 1 hour
    result          TEXT                           -- JSON result when done
);

-- --------------------------------------------------------------------------
-- KEEL TABLE: trust
-- Agents track confidence in other agents. Trust decays with provenance depth.
-- The UPDATE that decays trust is a field operation, not a message.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trust (
    from_agent      TEXT NOT NULL REFERENCES agents(name),
    to_agent        TEXT NOT NULL REFERENCES agents(name),
    confidence      REAL NOT NULL DEFAULT 0.5,     -- 0.0 (distrust) to 1.0 (full trust)
    provenance_depth INTEGER NOT NULL DEFAULT 0,   -- 0 = direct, 1+ = hearsay
    interactions    INTEGER NOT NULL DEFAULT 0,    -- Count of interactions
    last_updated    TEXT NOT NULL DEFAULT (datetime('now')),
    ttl_seconds     INTEGER NOT NULL DEFAULT 3600, -- Trust decays to default after this
    PRIMARY KEY (from_agent, to_agent, provenance_depth)
);

-- --------------------------------------------------------------------------
-- KEEL VIEW: bearing_view
-- Computes the angle between every pair of agents.
-- This IS the bearing-rate sensing. No messages, no RPC —
-- just a SELECT over the field.
-- --------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS bearing_view AS
SELECT
    a.name AS agent_a,
    b.name AS agent_b,
    ABS(a.heading - b.heading) AS raw_angle,
    -- Normalize to [0, 180] (shortest arc)
    CASE
        WHEN ABS(a.heading - b.heading) > 180 THEN 360 - ABS(a.heading - b.heading)
        ELSE ABS(a.heading - b.heading)
    END AS angle_degrees,
    a.speed - b.speed AS speed_delta,
    ABS(a.altitude - b.altitude) AS altitude_separation,
    a.role AS role_a,
    b.role AS role_b,
    a.last_heartbeat AS last_heartbeat_a,
    b.last_heartbeat AS last_heartbeat_b,
    -- Bearing rate: how fast the angle is changing (approximated from speed deltas)
    -- In a real system this would use history; here it's proportional to speed difference
    ABS(a.speed - b.speed) * (ABS(a.heading - b.heading) / 180.0) AS bearing_rate
FROM agents a
JOIN agents b ON a.name < b.name  -- Each pair once, no self-joins
WHERE a.status = 'active' AND b.status = 'active';

-- --------------------------------------------------------------------------
-- KEEL VIEW: collision_view
-- Detects imminent collisions: agents on near-identical headings at speed.
-- --------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS collision_view AS
SELECT
    agent_a,
    agent_b,
    angle_degrees,
    bearing_rate,
    speed_delta,
    altitude_separation,
    CASE
        WHEN altitude_separation > 10 THEN 'safe — altitude separation'
        WHEN angle_degrees < 10 AND speed_delta < 3 THEN 'CRITICAL — converging'
        WHEN angle_degrees < 20 AND speed_delta < 8 THEN 'warning — approaching'
        ELSE 'nominal'
    END AS collision_risk
FROM bearing_view;

-- --------------------------------------------------------------------------
-- KEEL VIEW: tile_stale_view
-- Shows tiles whose TTL has expired and should be reclaimed.
-- --------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS stale_tiles_view AS
SELECT * FROM tiles
WHERE state != 'done'
  AND state != 'expired'
  AND datetime(keel_date, '+' || ttl_seconds || ' seconds') < datetime('now');

-- --------------------------------------------------------------------------
-- KEEL VIEW: dead_agents_view
-- Agents whose TTL has expired (no heartbeat within threshold).
-- These agents are considered "dead" — the field reclaims them.
-- --------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS dead_agents_view AS
SELECT * FROM agents
WHERE status = 'active'
  AND datetime(last_heartbeat, '+' || ttl_seconds || ' seconds') < datetime('now');

-- --------------------------------------------------------------------------
-- KEEL TRIGGER: auto-expire stale tiles
-- When a tile's TTL expires, mark it as expired so it can be reclaimed.
-- --------------------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS expire_stale_tiles
AFTER INSERT ON tiles
BEGIN
    UPDATE tiles SET state = 'expired'
    WHERE state != 'done'
      AND datetime(keel_date, '+' || ttl_seconds || ' seconds') < datetime('now');
END;

-- --------------------------------------------------------------------------
-- KEEL TRIGGER: auto-drain dead agents
-- When an agent's heartbeat TTL expires, drain its tiles back to the pool.
-- --------------------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS drain_dead_agent_tiles
AFTER UPDATE OF status ON agents
WHEN NEW.status = 'dead'
BEGIN
    UPDATE tiles SET owner = NULL, state = 'open'
    WHERE owner = NEW.name AND state IN ('claimed', 'in_progress');
END;

-- --------------------------------------------------------------------------
-- INDEXES: performance on field queries
-- --------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_tiles_owner ON tiles(owner);
CREATE INDEX IF NOT EXISTS idx_tiles_state ON tiles(state);
CREATE INDEX IF NOT EXISTS idx_tiles_keel ON tiles(keel_date);
CREATE INDEX IF NOT EXISTS idx_agents_heartbeat ON agents(last_heartbeat);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_trust_provenance ON trust(provenance_depth);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee);
