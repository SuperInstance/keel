// ═══════════════════════════════════════════════════════════════
// core.es — Keel Event Types (Pseudocode)
// The Keel TTL Engine: Event-Sourced First-Person Self-Termination
// ═══════════════════════════════════════════════════════════════
// The event store is the only truth.
// Everything else is a projection.
// TTL is not a stored field — it is derived from the projection.
// Death is not stored — it is the absence of later events.
// ═══════════════════════════════════════════════════════════════

// ─── TILE EVENTS ──────────────────────────────────────────────

event TileCreated {
    tile_id: UUID
    keel_date: Timestamp        // when this tile was laid down
    ttl: Duration               // time-to-live after keel_date
    tile_type: String           // e.g. "hull", "deck", "engine"
    data: Map<String, Any>      // tile-specific payload
}

// TileExpired is NOT an event. It is a projected state.
// When current_time - keel_date > ttl, the tile is expired.
// The projection computes this; no event is stored.
// Expiry is not a thing that happens — it is a thing that IS true.
projection TileExpired {
    tile_id: UUID
    derived_from: TileCreated
    condition: now - TileCreated.keel_date > TileCreated.ttl
}

// ─── TASK EVENTS ──────────────────────────────────────────────

event TaskCreated {
    task_id: UUID
    created: Timestamp
    ttl: Duration               // task expires if incomplete past ttl
    description: String
    steps: List<String>         // ordered steps to complete
}

event TaskStepCompleted {
    task_id: UUID
    step_index: Int
    completed_at: Timestamp
}

// TaskExpired is a projected state, not an event.
// Condition: no TaskStepCompleted for all steps, and now - created > ttl
// Or: the task was never fully completed within its ttl window
projection TaskExpired {
    task_id: UUID
    derived_from: TaskCreated ∧ (¬TaskStepCompleted[all_steps])
    condition: now - TaskCreated.created > TaskCreated.ttl
                    ∧ incomplete(TaskCreated.steps, TaskStepCompleted)
}

// ─── AGENT EVENTS ─────────────────────────────────────────────

event AgentSpawned {
    agent_id: UUID
    keel_date: Timestamp        // first appearance / launch
    ttl: Duration               // lifespan
    heading: String             // purpose / direction
    spawner_id: UUID            // who created this agent
}

event AgentHeartbeat {
    agent_id: UUID
    timestamp: Timestamp        // latest sign of life
}

// AgentSilent is a projected state.
// Condition: last AgentHeartbeat is older than AgentSpawned.ttl
// OR: no AgentHeartbeat since AgentSpawned and now - keel_date > ttl
// An agent that stops producing heartbeats is not "dead."
// It is simply an entity whose last event is AgentSpawned
// with no following events. The field computes this.
projection AgentSilent {
    agent_id: UUID
    derived_from: AgentSpawned[last] ∧ AgentHeartbeat[last]
    condition: now - max(AgentSpawned.keel_date, AgentHeartbeat.timestamp) 
                   > AgentSpawned.ttl
}

// ─── BEARING EVENTS (Field Observation) ──────────────────────

event BearingObserved {
    observer: UUID              // who saw something
    target: UUID                // what was seen
    angle: Float                // relative bearing in degrees
    rate: Float                 // rate of change of bearing
    observed_at: Timestamp
}

// BearingStale is a projected state.
// Bearing observations decay. If no new BearingObserved within threshold,
// the bearing is stale. The observer hasn't reported — the field forgets.
projection BearingStale {
    observer: UUID
    target: UUID
    derived_from: BearingObserved[last_for_pair]
    condition: now - BearingObserved.observed_at > BEARING_TTL
}

// ─── TRUST EVENTS ────────────────────────────────────────────

event TrustAsserted {
    subject: UUID              // who is claiming trust
    claim: String              // what the trust claim is about
    confidence: Float          // 0.0 to 1.0
    depth: Int                 // how many hops of delegation
    asserted_at: Timestamp
}

event TrustDecayed {
    subject: UUID
    claim: String
    new_confidence: Float      // after decay applied
}

// ─── FIELD PRINCIPLES ─────────────────────────────────────────
//
// 1. FIRST-PERSON SELF-TERMINATION
//    Each entity carries its own death, encoded as a TTL in its
//    creation event. No central scheduler. No death certificate.
//    The entity doesn't die — it is simply not present in the
//    projection when the field looks.
//
// 2. THE PROJECTION IS THE FIELD
//    The event store is pure history. The projection is the field.
//    Every query is a projection. Every view is derived by replay.
//    The field is not stored — it is computed.
//
// 3. DEATH IS THE ABSENCE OF LATER EVENTS
//    There is no "death" event. Death is a mathematical property
//    of the projection: the last event for this entity is farther
//    in the past than its declared TTL. The entity simply stops
//    appearing in queries that require liveness.
//
// 4. EVENTS ARE APPEND-ONLY, PROJECTIONS ARE EPHEMERAL
//    Events never change. Projections are rebuilt on demand.
//    You can always recompute the field from the event store.
//    This makes the system auditable, replayable, and debuggable.
//
// 5. THE BEARING IS THE COMMAND
//    BearingObserved events are sensor readings. The field doesn't
//    decide what to observe — it receives observations. The bearing
//    IS the command: "I saw X at angle Y, moving at rate Z."
//    The field projects what it means.
