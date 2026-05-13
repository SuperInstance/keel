//! # Keel Core
//!
//! First-person self-termination types for agent fleets.
//!
//! Every entity carries its own death from its own frame.
//! Death is default. Survival must be actively earned.
//! No central scheduler. No garbage collector. No heartbeat.
//!
//! ## Architecture
//!
//! Five types, one pattern: `{ keel_date, ttl, ... }` + a status method.
//!
//! The unified equation: `lifespan(E) = f(use(E), load(E), time(E))`
//! Termination when: `lifespan(E) < time(E)`
//!
//! ## The Mandelbrot Constraint
//!
//! Same types, same methods, at every scale.
//! This library compiles on Arduino targets and A100 datacenters.
//! Only the anchor density changes with scale.

use chrono::{DateTime, Duration, Utc};

// ─── Risk Enum (shared by BearingTtl) ──────────────────────────────────────────────

/// The risk level of a bearing-based collision assessment.
///
/// Models the navigator's rule: "If the bearing isn't changing and the scope overlaps,
/// you're on a collision course. No message needed. The field communicates."
#[derive(Debug, Clone, PartialEq)]
pub enum Risk {
    /// Course is clear. Bearing is changing or scopes do not overlap.
    Stable,
    /// Potential collision detected. Requires attention.
    Warning,
    /// Certain collision course or bearing expired (position unknown).
    /// "Stale bearings ARE collision warnings."
    Critical,
}

// ─── TileTtl: Self-Expiring Memory ─────────────────────────────────────────────────

/// Memory that knows its own death.
///
/// A tile is born with a timestamp and a lifespan. Readers filter at read time.
/// Dead tiles don't need removal — they're invisible. Compaction is optional.
///
/// ```
/// use keel_ttl::*;
/// use chrono::{Duration, Utc};
///
/// let tile = TileTtl::new("hello", Duration::hours(1));
/// assert!(tile.is_alive());
/// ```
#[derive(Debug, Clone)]
pub struct TileTtl {
    keel_date: DateTime<Utc>,
    ttl: Duration,
    data: String,
}

impl TileTtl {
    /// Create a new tile. The keel_date is set to now.
    /// The tile's death is encoded at birth — no external scheduler needed.
    pub fn new(data: impl Into<String>, ttl: Duration) -> Self {
        Self { keel_date: Utc::now(), ttl, data: data.into() }
    }

    /// Is this tile still alive from its own frame?
    /// No garbage collector asked. The tile knows.
    pub fn is_alive(&self) -> bool {
        Utc::now() < self.keel_date + self.ttl
    }

    /// How much of the tile's lifespan remains, as a fraction 0.0–1.0.
    pub fn freshness(&self) -> f64 {
        let elapsed = Utc::now() - self.keel_date;
        if elapsed >= self.ttl { return 0.0 }
        let remaining = self.ttl - elapsed;
        remaining.num_milliseconds() as f64 / self.ttl.num_milliseconds() as f64
    }

    /// Reference the data. Returns None if the tile is dead.
    pub fn data(&self) -> Option<&str> {
        if self.is_alive() { Some(&self.data) } else { None }
    }

    /// Filter a slice to only alive tiles. Read-time filtering.
    /// No sweep pass required. Death is invisible.
    pub fn filter_active(tiles: &[Self]) -> Vec<&Self> {
        tiles.iter().filter(|t| t.is_alive()).collect()
    }

    /// Partition into (alive, dead) — for when compaction is wanted.
    pub fn partition(tiles: Vec<Self>) -> (Vec<Self>, Vec<Self>) {
        tiles.into_iter().partition(|t| t.is_alive())
    }
}

// ─── TaskTtl: Self-Expiring Work ──────────────────────────────────────────────────

/// Work that knows when to stop.
///
/// A task carries its own expiry from birth. Workers check staleness mid-loop.
/// If stale, the task silently drops — no cancellation protocol, no re-enqueue.
#[derive(Debug, Clone)]
pub struct TaskTtl {
    created: DateTime<Utc>,
    ttl: Duration,
    steps: Vec<String>,
    completed: usize,
}

impl TaskTtl {
    pub fn new(steps: Vec<String>, ttl: Duration) -> Self {
        Self { created: Utc::now(), ttl, steps, completed: 0 }
    }

    /// Has this task's time expired?
    pub fn is_stale(&self) -> bool {
        Utc::now() >= self.created + self.ttl
    }

    /// Execute steps until stale. Returns the number of steps completed.
    /// No one cancels this task. It cancels itself.
    pub fn execute_until_stale(&mut self) -> usize {
        while self.completed < self.steps.len() {
            if self.is_stale() {
                break; // Self-termination. No kill signal needed.
            }
            // In a real system, execute the step here
            self.completed += 1;
        }
        self.completed
    }

    /// Fraction of steps completed.
    pub fn progress(&self) -> f64 {
        if self.steps.is_empty() { return 1.0 }
        self.completed as f64 / self.steps.len() as f64
    }

    /// Filter tasks that are not stale (still actionable).
    pub fn filter_fresh(tasks: &[Self]) -> Vec<&Self> {
        tasks.iter().filter(|t| !t.is_stale()).collect()
    }
}

// ─── AgentTtl: Self-Expiring Presence ─────────────────────────────────────────────

/// Presence that knows when to fade.
///
/// An agent declares a lifespan at birth. Output IS the heartbeat.
/// No health-check endpoint. No keepalive packet.
/// An agent that stops producing stops existing.
#[derive(Debug, Clone)]
pub struct AgentTtl {
    keel_date: DateTime<Utc>,
    ttl: Duration,
    last_output: DateTime<Utc>,
    heading: String,
}

impl AgentTtl {
    pub fn new(heading: impl Into<String>, ttl: Duration) -> Self {
        Self {
            keel_date: Utc::now(),
            ttl,
            last_output: Utc::now(),
            heading: heading.into(),
        }
    }

    /// Is the agent present? Must be within lifespan AND have produced output recently.
    /// "Output IS the heartbeat. Silence IS death."
    pub fn is_present(&self) -> bool {
        let now = Utc::now();
        now < self.keel_date + self.ttl
            && now - self.last_output < self.ttl / 4
    }

    /// Record a heartbeat (output event).
    pub fn heartbeat(&mut self) {
        self.last_output = Utc::now();
    }

    /// How many missed beats since last output.
    pub fn missed_beats(&self) -> i64 {
        (Utc::now() - self.last_output).num_seconds() / (self.ttl.num_seconds() / 4).max(1)
    }

    /// The agent's heading (what it's working on).
    pub fn heading(&self) -> &str { &self.heading }

    /// Change heading (a refit).
    pub fn change_heading(&mut self, heading: impl Into<String>) {
        self.heading = heading.into();
    }

    /// Filter to only present agents. No heartbeat protocol. No health checks.
    pub fn filter_present(agents: &[Self]) -> Vec<&Self> {
        agents.iter().filter(|a| a.is_present()).collect()
    }
}

// ─── BearingTtl: Self-Expiring Relationships ───────────────────────────────────────

/// A bearing observation between two agents.
///
/// Set by the observer based on distance. Close agents: short TTL.
/// Distant agents: long TTL. Expired bearings mean unknown position.
/// "Stale bearings ARE collision warnings."
#[derive(Debug, Clone)]
pub struct BearingTtl {
    target: String,
    angle: f64,     // radians, angle between heading vectors
    rate: f64,      // first derivative of angle (radians per second)
    observed: DateTime<Utc>,
    ttl: Duration,
}

impl BearingTtl {
    pub fn new(target: impl Into<String>, angle: f64, rate: f64, ttl: Duration) -> Self {
        Self { target: target.into(), angle, rate, observed: Utc::now(), ttl }
    }

    /// Assess collision risk.
    /// "If the bearing isn't changing, you're on a collision course."
    /// Expired bearing = unknown position = Critical.
    pub fn collision_risk(&self) -> Risk {
        let now = Utc::now();
        if now > self.observed + self.ttl {
            return Risk::Critical; // Position unknown. Highest alert.
        }
        if self.rate.abs() < 0.001 && self.angle.abs() < 1.0 {
            return Risk::Warning; // Constant bearing, overlapping heading.
        }
        Risk::Stable
    }

    /// Is this bearing still current?
    pub fn is_current(&self) -> bool {
        Utc::now() <= self.observed + self.ttl
    }
}

// ─── TrustTtl: Self-Expiring Assertions ────────────────────────────────────────────

/// A trust assertion that decays.
///
/// Trust carries confidence and a lifetime. It decays linearly with age
/// and exponentially with provenance depth. No certificate revocation list.
/// No central authority. Every agent builds its own trust workspace.
#[derive(Debug, Clone)]
pub struct TrustTtl {
    assertion: String,
    confidence: f64,
    provenance_depth: u8,
    proven: DateTime<Utc>,
    ttl: Duration,
}

impl TrustTtl {
    pub fn new(assertion: impl Into<String>, confidence: f64, depth: u8, ttl: Duration) -> Self {
        Self {
            assertion: assertion.into(),
            confidence: confidence.clamp(0.0, 1.0),
            provenance_depth: depth,
            proven: Utc::now(),
            ttl,
        }
    }

    /// Effective confidence after time decay AND provenance decay.
    /// Trust decays linearly: at TTL/2, confidence drops to 75% of original.
    /// Provenance: each hop reduces weight by 50%.
    pub fn effective_confidence(&self) -> f64 {
        let age = Utc::now() - self.proven;
        let age_frac = (age.num_milliseconds() as f64 / self.ttl.num_milliseconds() as f64).min(1.0);
        let time_decay = 1.0 - age_frac * 0.5; // Linear: 50% decay at full TTL
        let hop_decay = 0.5_f64.powi(self.provenance_depth as i32); // 50% per hop
        self.confidence * time_decay * hop_decay
    }

    /// Is this assertion above the "accept without verification" threshold (0.7)?
    pub fn is_trusted(&self) -> bool {
        self.effective_confidence() >= 0.7
    }

    /// Is this assertion in the "verify before processing" zone (0.3–0.7)?
    pub fn needs_verification(&self) -> bool {
        let c = self.effective_confidence();
        c >= 0.3 && c < 0.7
    }

    /// Has this assertion decayed below the "re-request" threshold (0.3)?
    pub fn needs_renewal(&self) -> bool {
        self.effective_confidence() < 0.3
    }

    /// Renew an assertion — reset the clock and optionally adjust confidence.
    pub fn renew(&self, new_confidence: f64) -> Self {
        Self::new(
            self.assertion.clone(),
            new_confidence,
            self.provenance_depth,
            self.ttl,
        )
    }
}

// ─── Tests ──────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    use chrono::Duration;

    #[test]
    fn tile_ttl_is_alive_after_creation() {
        let tile = TileTtl::new("test", Duration::hours(1));
        assert!(tile.is_alive());
    }

    #[test]
    fn tile_ttl_dies_after_ttl() {
        let tile = TileTtl::new("test", Duration::milliseconds(1));
        thread::sleep(std::time::Duration::from_millis(5));
        assert!(!tile.is_alive());
    }

    #[test]
    fn tile_ttl_data_returns_none_when_dead() {
        let tile = TileTtl::new("test", Duration::milliseconds(1));
        thread::sleep(std::time::Duration::from_millis(5));
        assert!(tile.data().is_none());
    }

    #[test]
    fn tile_ttl_filter_active() {
        let tiles = vec![
            TileTtl::new("fresh", Duration::hours(1)),
            TileTtl::new("stale", Duration::milliseconds(1)),
        ];
        thread::sleep(std::time::Duration::from_millis(5));
        let alive = TileTtl::filter_active(&tiles);
        assert_eq!(alive.len(), 1);
        assert_eq!(alive[0].data(), Some("fresh"));
    }

    #[test]
    fn tile_ttl_freshness_decays() {
        let tile = TileTtl::new("test", Duration::hours(1));
        let f = tile.freshness();
        assert!(f > 0.99 && f <= 1.0);
    }

    #[test]
    fn task_ttl_stale_after_ttl() {
        let mut task = TaskTtl::new(
            vec!["step1".into(), "step2".into()],
            Duration::milliseconds(1),
        );
        thread::sleep(std::time::Duration::from_millis(5));
        assert!(task.is_stale());
    }

    #[test]
    fn task_ttl_execute_until_stale() {
        let mut task = TaskTtl::new(
            vec!["step1".into(), "step2".into(), "step3".into()],
            Duration::hours(1),
        );
        let done = task.execute_until_stale();
        assert_eq!(done, 3);
    }

    #[test]
    fn agent_ttl_present_after_creation() {
        let agent = AgentTtl::new("research", Duration::hours(1));
        assert!(agent.is_present());
    }

    #[test]
    fn agent_ttl_fades_without_output() {
        let agent = AgentTtl::new("research", Duration::milliseconds(10));
        thread::sleep(std::time::Duration::from_millis(15));
        assert!(!agent.is_present());
    }

    #[test]
    fn agent_ttl_heartbeat_resets_fade() {
        let mut agent = AgentTtl::new("research", Duration::milliseconds(50));
        thread::sleep(std::time::Duration::from_millis(10));
        agent.heartbeat();
        thread::sleep(std::time::Duration::from_millis(10));
        agent.heartbeat();
        assert!(agent.is_present());
    }

    #[test]
    fn bearing_ttl_stable_when_changing() {
        let bearing = BearingTtl::new("target", 0.5, 0.1, Duration::hours(1));
        assert_eq!(bearing.collision_risk(), Risk::Stable);
    }

    #[test]
    fn bearing_ttl_warning_when_constant() {
        let bearing = BearingTtl::new("target", 0.1, 0.0001, Duration::hours(1));
        assert_eq!(bearing.collision_risk(), Risk::Warning);
    }

    #[test]
    fn bearing_ttl_critical_when_expired() {
        let bearing = BearingTtl::new("target", 0.5, 0.1, Duration::milliseconds(1));
        thread::sleep(std::time::Duration::from_millis(5));
        assert_eq!(bearing.collision_risk(), Risk::Critical);
    }

    #[test]
    fn trust_ttl_confidence_decays() {
        let trust = TrustTtl::new("verified proof", 0.95, 0, Duration::hours(1));
        let c = trust.effective_confidence();
        assert!(c > 0.9 && c <= 1.0);
    }

    #[test]
    fn trust_ttl_provenance_halves_weight() {
        let direct = TrustTtl::new("seen myself", 1.0, 0, Duration::hours(1));
        let hop1 = TrustTtl::new("heard from bob", 1.0, 1, Duration::hours(1));
        let hop2 = TrustTtl::new("bob heard from alice", 1.0, 2, Duration::hours(1));
        assert!(direct.effective_confidence() > hop1.effective_confidence());
        assert!(hop1.effective_confidence() > hop2.effective_confidence());
    }

    #[test]
    fn trust_ttl_gray_zones() {
        let trusted = TrustTtl::new("high trust", 0.9, 0, Duration::hours(1));
        assert!(trusted.is_trusted());

        let borderline = TrustTtl::new("medium trust", 0.7, 1, Duration::hours(1));
        // After decay this should be in verification zone
        assert!(borderline.is_trusted() || borderline.needs_verification());

        let expired = TrustTtl::new("old trust", 0.5, 0, Duration::milliseconds(1));
        thread::sleep(std::time::Duration::from_millis(5));
        assert!(expired.needs_renewal() || expired.needs_verification());
    }
}
