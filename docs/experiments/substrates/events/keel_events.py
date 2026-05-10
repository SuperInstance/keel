#!/usr/bin/env python3
"""
keel_events.py — Keel TTL Engine Event Store

"The event store is the only truth. Everything else is a projection.
 TTL is not a field on the data — it's a property of the projection.
 Death is not stored — it's derived."

Architecture:
    EventStore      → append-only log of domain events
    Projections     → derived views computed by replaying events
    TTL             → not stored; projected from creation time + ttl value

Key insight: death is the absence of later events. An agent that stops
producing heartbeats isn't "dead" — it's simply an entity whose last
event is AgentSpawned with no following events. The field projection
IS the first-person self-termination computation.
"""

from __future__ import annotations

import uuid
import time
import itertools
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

# ─── Event Types (Domain Events) ───────────────────────────────

@dataclass
class Event:
    """Base event — all domain events inherit from this."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TileCreated(Event):
    event_type: str = "TileCreated"
    tile_id: str = ""
    keel_date: float = 0.0
    ttl: float = 0.0
    tile_type: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskCreated(Event):
    event_type: str = "TaskCreated"
    task_id: str = ""
    created: float = 0.0
    ttl: float = 0.0
    description: str = ""
    steps: List[str] = field(default_factory=list)


@dataclass
class TaskStepCompleted(Event):
    event_type: str = "TaskStepCompleted"
    task_id: str = ""
    step_index: int = 0
    completed_at: float = 0.0


@dataclass
class AgentSpawned(Event):
    event_type: str = "AgentSpawned"
    agent_id: str = ""
    keel_date: float = 0.0
    ttl: float = 0.0
    heading: str = ""
    spawner_id: str = ""


@dataclass
class AgentHeartbeat(Event):
    event_type: str = "AgentHeartbeat"
    agent_id: str = ""
    timestamp: float = 0.0


@dataclass
class BearingObserved(Event):
    event_type: str = "BearingObserved"
    observer: str = ""
    target: str = ""
    angle: float = 0.0
    rate: float = 0.0
    observed_at: float = 0.0


@dataclass
class TrustAsserted(Event):
    event_type: str = "TrustAsserted"
    subject: str = ""
    claim: str = ""
    confidence: float = 0.0
    depth: int = 0
    asserted_at: float = 0.0


@dataclass
class TrustDecayed(Event):
    event_type: str = "TrustDecayed"
    subject: str = ""
    claim: str = ""
    new_confidence: float = 0.0


# Event registry: maps event_type string to class
EVENT_TYPES: Dict[str, type] = {
    "TileCreated": TileCreated,
    "TaskCreated": TaskCreated,
    "TaskStepCompleted": TaskStepCompleted,
    "AgentSpawned": AgentSpawned,
    "AgentHeartbeat": AgentHeartbeat,
    "BearingObserved": BearingObserved,
    "TrustAsserted": TrustAsserted,
    "TrustDecayed": TrustDecayed,
}


# ─── Event Store ──────────────────────────────────────────────

class EventStore:
    """
    Append-only event store.
    
    The event store is the only truth. Events are never modified,
    deleted, or reordered. New events are always appended.
    """

    def __init__(self) -> None:
        self._events: List[Event] = []
        self._sequence: int = 0

    def append(self, event: Event) -> int:
        """Append an event. Returns its sequence number."""
        self._sequence += 1
        event.timestamp = event.timestamp or time.time()
        self._events.append(event)
        return self._sequence

    def read_all(self) -> List[Event]:
        """Read every event in order."""
        return self._events.copy()

    def read_by_type(self, event_type: str) -> List[Event]:
        """Filter events by type string."""
        return [e for e in self._events if e.event_type == event_type]

    def read_by_entity(self, entity_id_field: str, entity_id: str) -> List[Event]:
        """Filter events for a specific entity (tile, agent, task, etc.)."""
        return [e for e in self._events if hasattr(e, entity_id_field) 
                and getattr(e, entity_id_field) == entity_id]

    def replay(self, 
               filter_fn: Optional[Callable[[Event], bool]] = None,
               transform_fn: Optional[Callable[[Event, Any], Any]] = None,
               initial_state: Any = None) -> Any:
        """
        Generic replay: fold over events with an optional filter.
        
        Args:
            filter_fn: If provided, only events matching this predicate are replayed.
            transform_fn: If provided, called as transform_fn(event, state) → new_state.
            initial_state: Starting state for the fold.
        
        Returns:
            The final state after replaying all matching events.
        """
        state = initial_state
        for event in self._events:
            if filter_fn is None or filter_fn(event):
                if transform_fn:
                    state = transform_fn(event, state)
        return state

    def count(self) -> int:
        return len(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def __repr__(self) -> str:
        return f"EventStore({len(self._events)} events)"


# ─── BEARING TTL CONSTANT ─────────────────────────────────────
# In the real system this would be configurable per observer or per context.
# For this model we use a global constant.
BEARING_TTL: float = 300.0  # 5 minutes


# ─── PROJECTIONS ──────────────────────────────────────────────
#
# Each projection is a view derived from replaying relevant events.
# The projection IS the field — it computes what IS true right now.
# TTL is not a field on the data. It is computed by the projection.
# Death is not stored. It is the absence of recent events.

def _now() -> float:
    """Current time for projection computations. Override in tests."""
    return time.time()


# --- TileProjection ---

@dataclass
class TileState:
    tile_id: str
    keel_date: float
    ttl: float
    tile_type: str
    data: Dict[str, Any]
    alive: bool = True  # projected, not stored


class TileProjection:
    """
    Projection of all tiles from TileCreated events.
    
    TTL expiry is derived: if now - keel_date > ttl, the tile
    is projected as expired. No TileExpired event is stored.
    """

    def __init__(self, store: EventStore, now: Optional[float] = None) -> None:
        self._store = store
        self._now = now or _now()
        self._tiles: Dict[str, TileState] = {}
        self._rebuild()

    def _rebuild(self) -> None:
        """Rebuild the entire projection from the event store."""
        self._tiles = {}
        for event in self._store.read_by_type("TileCreated"):
            e = event  # type: TileCreated
            self._tiles[e.tile_id] = TileState(
                tile_id=e.tile_id,
                keel_date=e.keel_date,
                ttl=e.ttl,
                tile_type=e.tile_type,
                data=e.data,
                alive=(self._now - e.keel_date) <= e.ttl,
            )

    def refresh(self, now: Optional[float] = None) -> None:
        """Update the projection's time reference and recompute."""
        if now is not None:
            self._now = now
        for tile in self._tiles.values():
            tile.alive = (self._now - tile.keel_date) <= tile.ttl

    def get_tile(self, tile_id: str) -> Optional[TileState]:
        return self._tiles.get(tile_id)

    def alive_tiles(self) -> List[TileState]:
        return [t for t in self._tiles.values() if t.alive]

    def expired_tiles(self) -> List[TileState]:
        return [t for t in self._tiles.values() if not t.alive]

    def all_tiles(self) -> List[TileState]:
        return list(self._tiles.values())


# --- AgentProjection ---

@dataclass
class AgentState:
    agent_id: str
    keel_date: float
    ttl: float
    heading: str
    spawner_id: str
    last_heartbeat: Optional[float] = None
    alive: bool = True  # projected, not stored


class AgentProjection:
    """
    Projection of all agents from AgentSpawned + AgentHeartbeat events.
    
    An agent is alive if the elapsed time since its most recent
    life-marker event (keel_date or last heartbeat) is ≤ its TTL.
    
    If the agent stops producing heartbeats, it falls out of the
    alive set naturally — no AgentSilent event is needed.
    AgentSilent is the projection state where alive == False.
    """

    def __init__(self, store: EventStore, now: Optional[float] = None) -> None:
        self._store = store
        self._now = now or _now()
        self._agents: Dict[str, AgentState] = {}
        self._rebuild()

    def _rebuild(self) -> None:
        """Rebuild the projection from AgentSpawned and AgentHeartbeat events."""
        self._agents = {}

        # First pass: create agents from AgentSpawned
        for event in self._store.read_by_type("AgentSpawned"):
            e = event  # type: AgentSpawned
            self._agents[e.agent_id] = AgentState(
                agent_id=e.agent_id,
                keel_date=e.keel_date,
                ttl=e.ttl,
                heading=e.heading,
                spawner_id=e.spawner_id,
                last_heartbeat=None,
            )

        # Second pass: apply heartbeats
        for event in self._store.read_by_type("AgentHeartbeat"):
            e = event  # type: AgentHeartbeat
            if e.agent_id in self._agents:
                agent = self._agents[e.agent_id]
                if agent.last_heartbeat is None or e.timestamp > agent.last_heartbeat:
                    agent.last_heartbeat = e.timestamp

        # Third pass: compute liveness
        self._compute_liveness()

    def _compute_liveness(self) -> None:
        for agent in self._agents.values():
            latest = agent.last_heartbeat if agent.last_heartbeat is not None else agent.keel_date
            agent.alive = (self._now - latest) <= agent.ttl

    def refresh(self, now: Optional[float] = None) -> None:
        """Update the projection's time reference and recompute."""
        if now is not None:
            self._now = now
        self._compute_liveness()

    def get_agent(self, agent_id: str) -> Optional[AgentState]:
        return self._agents.get(agent_id)

    def alive_agents(self) -> List[AgentState]:
        return [a for a in self._agents.values() if a.alive]

    def silent_agents(self) -> List[AgentState]:
        return [a for a in self._agents.values() if not a.alive]

    def all_agents(self) -> List[AgentState]:
        return list(self._agents.values())


# --- TaskProjection ---

@dataclass
class TaskState:
    task_id: str
    created: float
    ttl: float
    description: str
    steps: List[str]
    completed_steps: set = field(default_factory=set)
    complete: bool = False
    expired: bool = False  # projected


class TaskProjection:
    """
    Projection of all tasks from TaskCreated + TaskStepCompleted events.
    
    A task is:
      - "complete" if all steps have TaskStepCompleted events
      - "expired" if not complete and now - created > ttl
      - "active" otherwise
    """

    def __init__(self, store: EventStore, now: Optional[float] = None) -> None:
        self._store = store
        self._now = now or _now()
        self._tasks: Dict[str, TaskState] = {}
        self._rebuild()

    def _rebuild(self) -> None:
        self._tasks = {}

        # First pass: create tasks
        for event in self._store.read_by_type("TaskCreated"):
            e = event  # type: TaskCreated
            self._tasks[e.task_id] = TaskState(
                task_id=e.task_id,
                created=e.created,
                ttl=e.ttl,
                description=e.description,
                steps=e.steps,
            )

        # Second pass: apply step completions
        for event in self._store.read_by_type("TaskStepCompleted"):
            e = event  # type: TaskStepCompleted
            if e.task_id in self._tasks:
                self._tasks[e.task_id].completed_steps.add(e.step_index)

        # Third pass: compute completion and expiry
        self._compute_status()

    def _compute_status(self) -> None:
        for task in self._tasks.values():
            task.complete = len(task.completed_steps) >= len(task.steps)
            task.expired = not task.complete and (self._now - task.created) > task.ttl

    def refresh(self, now: Optional[float] = None) -> None:
        if now is not None:
            self._now = now
        self._compute_status()

    def get_task(self, task_id: str) -> Optional[TaskState]:
        return self._tasks.get(task_id)

    def active_tasks(self) -> List[TaskState]:
        return [t for t in self._tasks.values() if not t.complete and not t.expired]

    def completed_tasks(self) -> List[TaskState]:
        return [t for t in self._tasks.values() if t.complete]

    def expired_tasks(self) -> List[TaskState]:
        return [t for t in self._tasks.values() if t.expired]

    def all_tasks(self) -> List[TaskState]:
        return list(self._tasks.values())


# --- BearingProjection ---

@dataclass
class BearingState:
    observer: str
    target: str
    angle: float
    rate: float
    observed_at: float
    stale: bool = False  # projected


class BearingProjection:
    """
    Projection of all observed bearings from BearingObserved events.
    
    A bearing is stale when no new observation has come in within
    BEARING_TTL seconds. Staleness is derived, not stored.
    """

    def __init__(self, store: EventStore, now: Optional[float] = None,
                 bearing_ttl: float = BEARING_TTL) -> None:
        self._store = store
        self._now = now or _now()
        self._bearing_ttl = bearing_ttl
        self._bearings: Dict[Tuple[str, str], BearingState] = {}
        self._rebuild()

    def _rebuild(self) -> None:
        self._bearings = {}
        # Process in order so only the latest observation per (observer, target) pair survives
        for event in self._store.read_by_type("BearingObserved"):
            e = event  # type: BearingObserved
            key = (e.observer, e.target)
            self._bearings[key] = BearingState(
                observer=e.observer,
                target=e.target,
                angle=e.angle,
                rate=e.rate,
                observed_at=e.observed_at,
                stale=(self._now - e.observed_at) > self._bearing_ttl,
            )

    def refresh(self, now: Optional[float] = None) -> None:
        if now is not None:
            self._now = now
        for bearing in self._bearings.values():
            bearing.stale = (self._now - bearing.observed_at) > self._bearing_ttl

    def get_bearing(self, observer: str, target: str) -> Optional[BearingState]:
        return self._bearings.get((observer, target))

    def fresh_bearings(self) -> List[BearingState]:
        return [b for b in self._bearings.values() if not b.stale]

    def stale_bearings(self) -> List[BearingState]:
        return [b for b in self._bearings.values() if b.stale]

    def all_bearings(self) -> List[BearingState]:
        return list(self._bearings.values())


# --- TrustProjection ---

@dataclass
class TrustState:
    subject: str
    claim: str
    confidence: float
    depth: int
    asserted_at: float


class TrustProjection:
    """
    Projection of all trust assertions from TrustAsserted + TrustDecayed events.
    
    Trust is a graph property. Each assertion is a directed edge from
    subject to claim with a confidence value and delegation depth.
    TrustDecayed events adjust confidence values over time.
    """

    def __init__(self, store: EventStore) -> None:
        self._store = store
        self._trusts: Dict[Tuple[str, str], TrustState] = {}
        self._rebuild()

    def _rebuild(self) -> None:
        self._trusts = {}
        for event in self._store.read_all():
            if event.event_type == "TrustAsserted":
                e = event  # type: TrustAsserted
                key = (e.subject, e.claim)
                self._trusts[key] = TrustState(
                    subject=e.subject,
                    claim=e.claim,
                    confidence=e.confidence,
                    depth=e.depth,
                    asserted_at=e.asserted_at,
                )
            elif event.event_type == "TrustDecayed":
                e = event  # type: TrustDecayed
                key = (e.subject, e.claim)
                if key in self._trusts:
                    self._trusts[key].confidence = e.new_confidence

    def get_trust(self, subject: str, claim: str) -> Optional[TrustState]:
        return self._trusts.get((subject, claim))

    def trust_for_subject(self, subject: str) -> List[TrustState]:
        return [t for k, t in self._trusts.items() if k[0] == subject]

    def trust_for_claim(self, claim: str) -> List[TrustState]:
        return [t for k, t in self._trusts.items() if k[1] == claim]

    def all_trusts(self) -> List[TrustState]:
        return list(self._trusts.values())


# ─── FIELD: Unified Projection ────────────────────────────────
#
# The Field combines all projections into a single view.
# This is what a query against "the system" actually sees.

@dataclass
class FieldState:
    """Snapshot of the entire derived field."""
    alive_tiles: List[TileState]
    expired_tiles: List[TileState]
    alive_agents: List[AgentState]
    silent_agents: List[AgentState]
    active_tasks: List[TaskState]
    completed_tasks: List[TaskState]
    expired_tasks: List[TaskState]
    fresh_bearings: List[BearingState]
    stale_bearings: List[BearingState]
    trust_assertions: List[TrustState]
    event_count: int
    timestamp: float


class Field:
    """
    The Field is the unified view of all projections.
    
    The Field is ephemeral — it is recomputed from the event store.
    The event store is the persistent truth. The Field is the
    derived reality, valid only for this moment.
    """

    def __init__(self, store: EventStore, now: Optional[float] = None) -> None:
        self.store = store
        self._now = now or _now()
        self.tiles = TileProjection(store, self._now)
        self.agents = AgentProjection(store, self._now)
        self.tasks = TaskProjection(store, self._now)
        self.bearings = BearingProjection(store, self._now)
        self.trusts = TrustProjection(store)

    def refresh(self, now: Optional[float] = None) -> None:
        """Recompute all projections. Call after appending new events."""
        if now is not None:
            self._now = now
        self.tiles.refresh(self._now)
        self.agents.refresh(self._now)
        self.tasks.refresh(self._now)
        self.bearings.refresh(self._now)

    def snapshot(self) -> FieldState:
        """Get a snapshot of everything in the field right now."""
        return FieldState(
            alive_tiles=self.tiles.alive_tiles(),
            expired_tiles=self.tiles.expired_tiles(),
            alive_agents=self.agents.alive_agents(),
            silent_agents=self.agents.silent_agents(),
            active_tasks=self.tasks.active_tasks(),
            completed_tasks=self.tasks.completed_tasks(),
            expired_tasks=self.tasks.expired_tasks(),
            fresh_bearings=self.bearings.fresh_bearings(),
            stale_bearings=self.bearings.stale_bearings(),
            trust_assertions=self.trusts.all_trusts(),
            event_count=len(self.store),
            timestamp=self._now,
        )

    def describe(self) -> str:
        """Human-readable description of the current field."""
        s = self.snapshot()
        lines = [
            f"═══ FIELD SNAPSHOT @ t={s.timestamp:.1f} ═══",
            f"Event store: {s.event_count} events",
            f"",
            f"── Tiles ──",
            f"  Alive:  {len(s.alive_tiles)}",
            f"  Expired: {len(s.expired_tiles)}",
            f"── Agents ──",
            f"  Alive:  {len(s.alive_agents)}",
            f"  Silent: {len(s.silent_agents)}",
            f"── Tasks ──",
            f"  Active:  {len(s.active_tasks)}",
            f"  Completed: {len(s.completed_tasks)}",
            f"  Expired:  {len(s.expired_tasks)}",
            f"── Bearings ──",
            f"  Fresh: {len(s.fresh_bearings)}",
            f"  Stale: {len(s.stale_bearings)}",
            f"── Trust ──",
            f"  Assertions: {len(s.trust_assertions)}",
        ]
        return "\n".join(lines)


# ─── DEPENDENCY INJECTION HELPERS ─────────────────────────────
# For production use, projections would accept a time provider
# so that time can be injected for testing and replay.

class SystemTime:
    """Default time provider — uses real wall clock."""

    @staticmethod
    def now() -> float:
        return time.time()


class FrozenTime:
    """Fixed time provider for testing and deterministic replay."""

    def __init__(self, fixed_time: float) -> None:
        self.fixed_time = fixed_time

    def now(self) -> float:
        return self.fixed_time

    def advance(self, seconds: float) -> None:
        self.fixed_time += seconds


# ─── SERIALIZATION ────────────────────────────────────────────
# Simple JSON-safe serialization for the event store.

def event_to_dict(event: Event) -> Dict[str, Any]:
    """Serialize an event to a dict (JSON-safe)."""
    d = asdict(event)
    return d


def dict_to_event(d: Dict[str, Any]) -> Event:
    """Deserialize a dict back to an Event."""
    event_type = d.get("event_type", "")
    cls = EVENT_TYPES.get(event_type)
    if cls is None:
        raise ValueError(f"Unknown event type: {event_type}")
    # Filter to only the fields the dataclass expects
    field_names = {f.name for f in cls.__dataclass_fields__.values()}
    filtered = {k: v for k, v in d.items() if k in field_names}
    return cls(**filtered)


# ─── FAST FORWARD / SNAPSHOT ─────────────────────────────────
# For large event stores, replaying from the beginning is expensive.
# Snapshots allow checkpoint-and-resume.

@dataclass
class Snapshot:
    """A snapshot of the field at a point in time."""
    sequence: int
    timestamp: float
    tiles: Dict[str, dict]
    agents: Dict[str, dict]
    tasks: Dict[str, dict]
    bearings: Dict[tuple, dict]
    trusts: Dict[tuple, dict]


def take_snapshot(field: Field) -> Snapshot:
    """Capture a snapshot of the current field for fast-forward recovery."""
    return Snapshot(
        sequence=len(field.store),
        timestamp=field._now,
        tiles={tid: asdict(t) for tid, t in field.tiles._tiles.items()},
        agents={aid: asdict(a) for aid, a in field.agents._agents.items()},
        tasks={tid: asdict(t) for tid, t in field.tasks._tasks.items()},
        bearings={k: asdict(b) for k, b in field.bearings._bearings.items()},
        trusts={k: asdict(t) for k, t in field.trusts._trusts.items()},
    )


if __name__ == "__main__":
    print("keel_events.py — Event Sourcing for the Keel TTL Engine")
    print("Run demo.py to see events in action.")
