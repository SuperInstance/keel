"""
keel_nats.py — Keel TTL Engine on NATS

"Death is default. The message carries its own death. No scheduler required."

NATS already has built-in TTL. Every message can carry a Nats-Msg-Timeout header
specifying its max age. JetStream has message retention policies with max_age for
automatic deletion. Subjects ARE the room protocol. Queue groups ARE agent pools.

This module is the Keel transport layer — pure Python using nats-py, no
central scheduler, no external dependency beyond NATS itself.

Subjects:
  keel.agent.{id}.heading   — agent heading (position, velocity, intention)
  keel.agent.{id}.heartbeat — agent heartbeat (TTL = main TTL/4)
  keel.bearing.{a}.{b}      — computed bearing between two agents
  keel.trust.{subject}      — trust assertions about an entity
  keel.tile.{room}          — PLATO-style tile storage (JetStream)
  keel.collision.>          — collision warnings (auto-published)

TTL is encoded in NATS headers:
  Nats-Msg-Timeout: <seconds>     — message-level TTL (NATS 2.10+)
  JetStream max_age               — store-level auto-expiry
  Consumer ack_wait               — delivery/acknowledgement window
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("keel_nats")

# ─── Constants ──────────────────────────────────────────────────────────────

DEFAULT_TTL = 30          # seconds — default message TTL
HEARTBEAT_TTL_DIVISOR = 4 # heartbeat TTL = heading TTL / 4
DEFAULT_BEARING_WINDOW = 5.0  # seconds — how long bearing data is valid
COLLISION_DISTANCE = 1.0      # units — collision threshold
COLLISION_LOOKAHEAD = 3.0     # seconds — collision prediction horizon

# ─── Subject Constants ─────────────────────────────────────────────────────

class Subjects:
    """NATS subject hierarchy for the Keel system."""
    HEADING = "keel.agent.{agent_id}.heading"
    HEARTBEAT = "keel.agent.{agent_id}.heartbeat"
    BEARING = "keel.bearing.{agent_a}.{agent_b}"
    TRUST = "keel.trust.{subject}"
    TILE = "keel.tile.{room}"
    COLLISION = "keel.collision"
    COLLISION_WILDCARD = "keel.collision.>"
    ALL_HEARTBEATS = "keel.agent.*.heartbeat"
    ALL_HEADINGS = "keel.agent.*.heading"
    ALL_BEARINGS = "keel.bearing.>"

# ─── Data Types ─────────────────────────────────────────────────────────────

@dataclass
class Position:
    """2D position in abstract space."""
    x: float
    y: float

    def distance_to(self, other: Position) -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def bearing_to(self, other: Position) -> float:
        """Bearing in radians from self to other."""
        return math.atan2(other.y - self.y, other.x - self.x)


@dataclass
class Velocity:
    """2D velocity vector."""
    vx: float
    vy: float

    @property
    def speed(self) -> float:
        return math.sqrt(self.vx ** 2 + self.vy ** 2)

    @property
    def heading_rad(self) -> float:
        """Direction of travel in radians."""
        return math.atan2(self.vy, self.vx)


@dataclass
class Heading:
    """Agent heading — position, velocity, intention."""
    agent_id: str
    position: Position
    velocity: Velocity
    intention: str = "cruising"   # cruising, fishing, returning, evading
    status: str = "active"        # active, drifting, disabled
    timestamp: float = field(default_factory=lambda: time.time())
    ttl: int = DEFAULT_TTL

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "position": asdict(self.position),
            "velocity": asdict(self.velocity),
            "intention": self.intention,
            "status": self.status,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Heading:
        return cls(
            agent_id=data["agent_id"],
            position=Position(**data["position"]),
            velocity=Velocity(**data["velocity"]),
            intention=data.get("intention", "cruising"),
            status=data.get("status", "active"),
            timestamp=data.get("timestamp", time.time()),
            ttl=data.get("ttl", DEFAULT_TTL),
        )


@dataclass
class Bearing:
    """Bearing between two agents."""
    agent_a: str
    agent_b: str
    distance: float
    bearing: float          # radians from A to B
    relative_speed: float   # closing speed
    time_to_closest: float  # seconds to closest approach (negative = passed)
    closest_distance: float # distance at closest approach
    timestamp: float = field(default_factory=lambda: time.time())

    @property
    def is_converging(self) -> bool:
        """True if agents are approaching each other."""
        return self.closest_distance < COLLISION_DISTANCE and self.time_to_closest > 0

    @property
    def collision_risk(self) -> float:
        """0.0 (safe) to 1.0 (imminent collision)."""
        if self.distance == 0:
            return 1.0
        if not self.is_converging:
            return 0.0
        # Closer + faster + imminent = higher risk
        proximity = max(0, 1.0 - self.closest_distance / COLLISION_DISTANCE)
        imminence = max(0, 1.0 - self.time_to_closest / COLLISION_LOOKAHEAD)
        return min(1.0, proximity * 0.6 + imminence * 0.4)

    def to_dict(self) -> dict:
        return {
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "distance": self.distance,
            "bearing": self.bearing,
            "relative_speed": self.relative_speed,
            "time_to_closest": self.time_to_closest,
            "closest_distance": self.closest_distance,
            "timestamp": self.timestamp,
            "is_converging": self.is_converging,
            "collision_risk": self.collision_risk,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Bearing:
        return cls(
            agent_a=data["agent_a"],
            agent_b=data["agent_b"],
            distance=data["distance"],
            bearing=data["bearing"],
            relative_speed=data["relative_speed"],
            time_to_closest=data["time_to_closest"],
            closest_distance=data["closest_distance"],
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class CollisionWarning:
    """Published when collision risk exceeds threshold."""
    agent_a: str
    agent_b: str
    risk: float
    time_to_impact: float
    distance: float
    warning_level: str  # advisory, warning, critical
    timestamp: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrustAssertion:
    """Trust assertion about an entity with decay."""
    subject: str
    trust_level: float       # 0.0 (distrust) to 1.0 (full trust)
    confidence: float        # 0.0 to 1.0
    assertion_type: str      # identity, capability, behavior
    evidence: str = ""       # optional evidence string
    timestamp: float = field(default_factory=lambda: time.time())
    decay_seconds: float = 3600.0  # trust decays to 0 after this

    @property
    def effective_trust(self) -> float:
        """Trust weighted by confidence and decay."""
        elapsed = time.time() - self.timestamp
        decay = max(0.0, 1.0 - elapsed / self.decay_seconds)
        return self.trust_level * self.confidence * decay

    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "effective_trust": self.effective_trust,
        }


# ─── Core Computation ──────────────────────────────────────────────────────

def compute_bearing(heading_a: Heading, heading_b: Heading) -> Bearing:
    """Compute bearing from agent_a to agent_b.

    Uses closest-point-of-approach (CPA) calculation to determine
    collision risk, time to closest approach, and closing speed.
    """
    # Relative position
    rx = heading_b.position.x - heading_a.position.x
    ry = heading_b.position.y - heading_a.position.y
    distance = math.sqrt(rx ** 2 + ry ** 2)

    # Relative velocity
    rvx = heading_b.velocity.vx - heading_a.velocity.vx
    rvy = heading_b.velocity.vy - heading_a.velocity.vy

    # CPA calculation
    rel_speed_sq = rvx ** 2 + rvy ** 2
    if rel_speed_sq < 0.0001:
        # No relative motion
        return Bearing(
            agent_a=heading_a.agent_id,
            agent_b=heading_b.agent_id,
            distance=distance,
            bearing=math.atan2(ry, rx),
            relative_speed=0.0,
            time_to_closest=float("inf"),
            closest_distance=distance,
        )

    # Time to closest approach
    # t = -(r·v) / (v·v)
    t_cpa = -(rx * rvx + ry * rvy) / rel_speed_sq
    if t_cpa < 0:
        t_cpa = 0.0  # already past closest approach

    # Distance at CPA
    closest_x = rx + rvx * t_cpa
    closest_y = ry + rvy * t_cpa
    closest_distance = math.sqrt(closest_x ** 2 + closest_y ** 2)

    # Closing speed (negative = opening)
    closing_speed = -(rx * rvx + ry * rvy) / distance if distance > 0 else 0

    bearing_rad = math.atan2(ry, rx)

    return Bearing(
        agent_a=heading_a.agent_id,
        agent_b=heading_b.agent_id,
        distance=distance,
        bearing=bearing_rad,
        relative_speed=closing_speed,
        time_to_closest=t_cpa,
        closest_distance=closest_distance,
    )


# ─── NATS Message Headers ──────────────────────────────────────────────────

def ttl_headers(ttl_seconds: int) -> dict:
    """Return NATS headers that encode TTL/death-as-default."""
    return {
        "Nats-Msg-Timeout": str(ttl_seconds),
        "Keel-TTL": str(ttl_seconds),
        "Keel-Sent": str(time.time()),
        "Keel-Version": "1.0",
    }


# ─── Keel Agent ─────────────────────────────────────────────────────────────

class KeelAgent:
    """An agent in the Keel fleet, communicating over NATS.

    Every agent publishes its heading with a TTL. If the agent stops
    publishing, its heading data dies. No central scheduler required.
    """

    def __init__(
        self,
        agent_id: str,
        nc: Any,  # nats NATS connection
        ttl: int = DEFAULT_TTL,
        heading: Optional[Heading] = None,
    ):
        self.agent_id = agent_id
        self.nc = nc
        self.ttl = ttl
        self.heading = heading or Heading(
            agent_id=agent_id,
            position=Position(0, 0),
            velocity=Velocity(0, 0),
        )
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heading_task: Optional[asyncio.Task] = None
        self._subscriptions: list = []

    async def publish_heading(self) -> None:
        """Publish current heading to NATS with TTL header.

        Each message carries its own death (Nats-Msg-Timeout).
        """
        self.heading.timestamp = time.time()
        self.heading.ttl = self.ttl
        data = json.dumps(self.heading.to_dict()).encode()
        subject = Subjects.HEADING.format(agent_id=self.agent_id)
        headers = ttl_headers(self.ttl)

        await self.nc.publish(subject, data, headers=headers)
        logger.debug(f"[{self.agent_id}] Published heading @ TTL={self.ttl}s")

    async def publish_heartbeat(self) -> None:
        """Publish heartbeat (TTL = main TTL / 4).

        Heartbeat dies faster than heading. If agent misses N consecutive
        heartbeats, it's presumed dead/disabled. Range is determined by
        heading TTL, liveness by heartbeat TTL.
        """
        data = json.dumps({
            "agent_id": self.agent_id,
            "timestamp": time.time(),
            "status": self.heading.status,
        }).encode()
        subject = Subjects.HEARTBEAT.format(agent_id=self.agent_id)
        hb_ttl = max(1, self.ttl // HEARTBEAT_TTL_DIVISOR)
        headers = ttl_headers(hb_ttl)

        await self.nc.publish(subject, data, headers=headers)
        logger.debug(f"[{self.agent_id}] Heartbeat @ TTL={hb_ttl}s")

    async def start(self) -> None:
        """Start periodic heading and heartbeat publishing.

        Agent publishes heading every TTL/2 and heartbeat every TTL/8,
        giving multiple chances to be heard before data expires.
        """
        self._running = True
        hb_interval = max(0.5, self.ttl / 8)
        heading_interval = max(1.0, self.ttl / 2)

        async def _heading_loop():
            while self._running:
                await self.publish_heading()
                await asyncio.sleep(heading_interval)

        async def _heartbeat_loop():
            while self._running:
                await self.publish_heartbeat()
                await asyncio.sleep(hb_interval)

        self._heading_task = asyncio.create_task(_heading_loop())
        self._heartbeat_task = asyncio.create_task(_heartbeat_loop())
        logger.info(f"[{self.agent_id}] Keel agent started (TTL={self.ttl}s)")

    async def stop(self) -> None:
        """Stop publishing. Data dies on its own — we don't clean it up.

        This is the point: death is default. When the agent stops publishing,
        its data expires naturally via NATS TTL. No explicit cleanup needed.
        """
        self._running = False
        if self._heading_task:
            self._heading_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        for sub in self._subscriptions:
            try:
                await sub.unsubscribe()
            except Exception:
                pass
        logger.info(f"[{self.agent_id}] Keel agent stopped — data will expire via TTL")

    async def update_position(self, x: float, y: float) -> None:
        """Update agent position."""
        self.heading.position = Position(x, y)

    async def update_velocity(self, vx: float, vy: float) -> None:
        """Update agent velocity."""
        self.heading.velocity = Velocity(vx, vy)

    async def set_intention(self, intention: str) -> None:
        """Set agent intention (cruising, fishing, returning, evading)."""
        self.heading.intention = intention

    async def set_status(self, status: str) -> None:
        """Set agent status (active, drifting, disabled)."""
        self.heading.status = status

    async def subscribe(self, subject: str, cb: Callable) -> Any:
        """Subscribe to a NATS subject with wildcard support."""
        sub = await self.nc.subscribe(subject, cb=cb)
        self._subscriptions.append(sub)
        return sub

    async def publish_trust(
        self,
        subject: str,
        trust_level: float,
        confidence: float = 1.0,
        assertion_type: str = "behavior",
        evidence: str = "",
        decay: float = 3600.0,
    ) -> None:
        """Publish a trust assertion with decay.

        Trust assertions have their own TTL (the decay period). When the
        decay expires, the trust is effectively zero — no explicit revocation
        needed.
        """
        assertion = TrustAssertion(
            subject=subject,
            trust_level=trust_level,
            confidence=confidence,
            assertion_type=assertion_type,
            evidence=evidence,
            decay_seconds=decay,
        )
        data = json.dumps(assertion.to_dict()).encode()
        nats_subject = Subjects.TRUST.format(subject=subject)
        await self.nc.publish(
            nats_subject, data,
            headers=ttl_headers(int(decay)),
        )


# ─── Bearing Watcher ────────────────────────────────────────────────────────

class BearingWatcher:
    """Subscribes to ALL headings and computes pairwise bearings.

    Each received heading is cached. When any heading changes, bearings
    to all other known agents are recomputed and published.

    Bearing data carries the minimum TTL of the two source headings,
    ensuring it dies at least as fast as its inputs.
    """

    def __init__(self, nc: Any, agent_id: str = "watcher"):
        self.nc = nc
        self.agent_id = agent_id
        self._headings: dict[str, Heading] = {}
        self._subscriptions: list = []
        self._running = False

    async def start(self) -> None:
        """Subscribe to all agent headings."""
        self._running = True
        sub = await self.nc.subscribe(
            Subjects.ALL_HEADINGS,
            cb=self._on_heading,
        )
        self._subscriptions.append(sub)
        logger.info(f"[{self.agent_id}] Bearing watcher started")

    async def stop(self) -> None:
        self._running = False
        for sub in self._subscriptions:
            try:
                await sub.unsubscribe()
            except Exception:
                pass

    async def _on_heading(self, msg: Any) -> None:
        """Handle incoming heading message."""
        try:
            data = json.loads(msg.data.decode())
            heading = Heading.from_dict(data)
            agent_id = heading.agent_id

            # Check if heading is still alive (within TTL)
            age = time.time() - heading.timestamp
            if age > heading.ttl:
                # Stale — remove from cache
                self._headings.pop(agent_id, None)
                return

            self._headings[agent_id] = heading

            # Recompute bearings with all other agents
            await self._recompute_bearings(agent_id)

        except Exception as e:
            logger.error(f"[{self.agent_id}] Bearing error: {e}")

    async def _recompute_bearings(self, changed_id: str) -> None:
        """Compute bearings for the changed agent against all others."""
        changed = self._headings.get(changed_id)
        if not changed:
            return

        for other_id, other_heading in list(self._headings.items()):
            if other_id == changed_id:
                continue

            # Ensure ordering is consistent for subject key
            a, b = sorted([changed_id, other_id])
            bearing_a = changed if a == changed_id else other_heading
            bearing_b = other_heading if a == changed_id else changed

            # Normalize: bearing from A to B
            if a == changed_id:
                bearing = compute_bearing(changed, other_heading)
            else:
                bearing = compute_bearing(other_heading, changed)

            subject = Subjects.BEARING.format(agent_a=a, agent_b=b)
            data = json.dumps(bearing.to_dict()).encode()

            # Bearing TTL = min of both source TTLs
            min_ttl = min(changed.ttl, other_heading.ttl)
            await self.nc.publish(
                subject, data,
                headers=ttl_headers(min_ttl),
            )

            # Check for collision
            if bearing.is_converging and bearing.collision_risk > 0.3:
                await self._publish_collision(bearing)

            logger.debug(
                f"[{self.agent_id}] Bearing {a}→{b}: "
                f"dist={bearing.distance:.2f}, "
                f"risk={bearing.collision_risk:.2f}"
            )

    async def _publish_collision(self, bearing: Bearing) -> None:
        """Publish collision warning based on bearing analysis."""
        level = "advisory"
        if bearing.collision_risk > 0.7:
            level = "critical"
        elif bearing.collision_risk > 0.5:
            level = "warning"

        warning = CollisionWarning(
            agent_a=bearing.agent_a,
            agent_b=bearing.agent_b,
            risk=bearing.collision_risk,
            time_to_impact=bearing.time_to_closest,
            distance=bearing.distance,
            warning_level=level,
        )

        data = json.dumps(warning.to_dict()).encode()
        subject = f"{Subjects.COLLISION}.{bearing.agent_a}.{bearing.agent_b}"

        # Collision warnings have short TTL — they're urgent and perishable
        await self.nc.publish(
            subject, data,
            headers=ttl_headers(max(5, int(bearing.time_to_closest))),
        )
        logger.warning(
            f"[{self.agent_id}] COLLISION {level.upper()}: "
            f"{bearing.agent_a} ↔ {bearing.agent_b} "
            f"(risk={bearing.collision_risk:.2f}, t={bearing.time_to_closest:.1f}s)"
        )

    def get_known_agents(self) -> list[str]:
        """Return list of agents with non-stale headings."""
        now = time.time()
        return [
            aid for aid, h in self._headings.items()
            if now - h.timestamp <= h.ttl
        ]


# ─── Collision Detector ────────────────────────────────────────────────────

class CollisionDetector:
    """Listens on keel.collision.> for collision warnings.

    Can aggregate warnings, log them, and trigger responses.
    Collision warnings self-terminate via their TTL.
    """

    def __init__(self, nc: Any, agent_id: str = "collision-detector"):
        self.nc = nc
        self.agent_id = agent_id
        self._subscriptions: list = []
        self._active_warnings: dict[str, CollisionWarning] = {}
        self._running = False
        self.on_collision: Optional[Callable[[CollisionWarning], Any]] = None

    async def start(self) -> None:
        self._running = True
        sub = await self.nc.subscribe(
            Subjects.COLLISION_WILDCARD,
            cb=self._on_warning,
        )
        self._subscriptions.append(sub)
        logger.info(f"[{self.agent_id}] Collision detector started")

    async def stop(self) -> None:
        self._running = False
        for sub in self._subscriptions:
            try:
                await sub.unsubscribe()
            except Exception:
                pass

    async def _on_warning(self, msg: Any) -> None:
        try:
            data = json.loads(msg.data.decode())
            warning = CollisionWarning(**data)
            key = f"{warning.agent_a}:{warning.agent_b}"
            self._active_warnings[key] = warning

            if self.on_collision:
                await self.on_collision(warning)

        except Exception as e:
            logger.error(f"[{self.agent_id}] Collision handler error: {e}")

    def prune_stale(self) -> None:
        """Remove warnings that have exceeded their useful lifetime."""
        now = time.time()
        stale = [
            k for k, w in self._active_warnings.items()
            if now - w.timestamp > 30  # warnings older than 30s are stale
        ]
        for k in stale:
            del self._active_warnings[k]

    @property
    def warnings(self) -> list[CollisionWarning]:
        self.prune_stale()
        return sorted(
            self._active_warnings.values(),
            key=lambda w: w.risk,
            reverse=True,
        )


# ─── Tile Store (JetStream) ────────────────────────────────────────────────

class TileStore:
    """PLATO-style tile storage using NATS JetStream.

    Tiles are key-value pairs published to keel.tile.{room} with
    JetStream persistence. Tiles have a max_age — they auto-expire
    like everything else in the Keel system.

    Note: Requires JetStream to be enabled on the NATS server.
    """

    def __init__(self, nc: Any, js: Any, agent_id: str = "tile-store"):
        self.nc = nc
        self.js = js
        self.agent_id = agent_id
        self._stream_name = "KEEL_TILES"

    async def create_stream(self) -> None:
        """Create or update the tile JetStream stream."""
        try:
            from nats.js.api import StreamConfig, StorageType, RetentionPolicy

            config = StreamConfig(
                name=self._stream_name,
                subjects=["keel.tile.>"],
                max_age=3600,               # tiles auto-expire after 1 hour
                max_bytes=10 * 1024 * 1024,  # 10MB max
                storage=StorageType.file,
                retention=RetentionPolicy.limits,
                discard="old",
            )
            await self.js.add_stream(config=config)
            logger.info(f"[{self.agent_id}] JetStream '{self._stream_name}' ready")
        except Exception:
            # Stream may already exist — that's fine
            pass

    async def put_tile(self, room: str, key: str, value: Any,
                       ttl_seconds: int = 3600) -> None:
        """Store a tile with automatic expiry."""
        subject = Subjects.TILE.format(room=room)
        data = json.dumps({
            "room": room,
            "key": key,
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl_seconds,
        }).encode()
        ack = await self.js.publish(
            subject, data,
            headers=ttl_headers(ttl_seconds),
        )
        logger.debug(f"[{self.agent_id}] Tile stored: {room}/{key}")

    async def get_tile(self, room: str, key_pattern: str = ">") -> list[dict]:
        """Retrieve tiles from a room (or all rooms with wildcard)."""
        subject = Subjects.TILE.format(room=room)
        if key_pattern and key_pattern != ">":
            subject = f"{subject}.{key_pattern}"

        results = []
        try:
            # Use ordered push consumer for simplicity
            sub = await self.js.pull_subscribe(
                subject, f"tile-reader-{self.agent_id}"
            )
            msgs = await sub.fetch(batch=100, timeout=2)
            for msg in msgs:
                try:
                    data = json.loads(msg.data.decode())
                    results.append(data)
                    await msg.ack()
                except Exception:
                    await msg.term()
            await sub.unsubscribe()
        except Exception:
            # Timeout or no messages — return whatever we got
            pass

        return results

    async def prune_expired(self) -> int:
        """Let JetStream handle expiry — this is a no-op.

        JetStream's max_age setting automatically deletes expired messages.
        The TTL header is for the message-level expiry; JetStream handles
        store-level expiry independently.
        """
        # JetStream handles this automatically.
        # This method exists as a reminder: death is default.
        return 0


# ─── Trust Registry ─────────────────────────────────────────────────────────

class TrustRegistry:
    """Receives trust assertions and tracks effective trust levels.

    Trust assertions self-decay via their TTL. No explicit revocation.
    """

    def __init__(self, nc: Any, agent_id: str = "trust-registry"):
        self.nc = nc
        self.agent_id = agent_id
        self._assertions: dict[str, list[TrustAssertion]] = {}
        self._subscriptions: list = []
        self._running = False

    async def start(self) -> None:
        self._running = True
        sub = await self.nc.subscribe(
            "keel.trust.>",
            cb=self._on_assertion,
        )
        self._subscriptions.append(sub)
        logger.info(f"[{self.agent_id}] Trust registry started")

    async def stop(self) -> None:
        self._running = False
        for sub in self._subscriptions:
            try:
                await sub.unsubscribe()
            except Exception:
                pass

    async def _on_assertion(self, msg: Any) -> None:
        try:
            data = json.loads(msg.data.decode())
            assertion = TrustAssertion(**{k: v for k, v in data.items()
                                           if k in TrustAssertion.__annotations__})
            subject = assertion.subject
            if subject not in self._assertions:
                self._assertions[subject] = []
            self._assertions[subject].append(assertion)

            # Prune expired
            self._assertions[subject] = [
                a for a in self._assertions[subject]
                if a.effective_trust > 0.01
            ]

            effective = assertion.effective_trust
            logger.debug(
                f"[{self.agent_id}] Trust [{subject}]: "
                f"level={assertion.trust_level}, "
                f"effective={effective:.2f}"
            )

        except Exception as e:
            logger.error(f"[{self.agent_id}] Trust error: {e}")

    def get_trust(self, subject: str) -> float:
        """Get aggregate effective trust for a subject."""
        assertions = self._assertions.get(subject, [])
        if not assertions:
            return 0.0
        # Average of effective trust values
        return sum(a.effective_trust for a in assertions) / len(assertions)

    def prune_all(self) -> None:
        """Remove expired assertions."""
        for subject in list(self._assertions.keys()):
            self._assertions[subject] = [
                a for a in self._assertions[subject]
                if a.effective_trust > 0.01
            ]
            if not self._assertions[subject]:
                del self._assertions[subject]


# ─── Keel System ────────────────────────────────────────────────────────────

class KeelNATS:
    """Top-level orchestrator for the Keel system on NATS.

    Manages agent lifecycle, bearing watcher, collision detector,
    tile store, and trust registry as a coordinated system.
    """

    def __init__(self, nc: Any, js: Any = None):
        self.nc = nc
        self.js = js
        self.agents: dict[str, KeelAgent] = {}
        self.watcher: Optional[BearingWatcher] = None
        self.collision_detector: Optional[CollisionDetector] = None
        self.tile_store: Optional[TileStore] = None
        self.trust_registry: Optional[TrustRegistry] = None
        self._running = False

    async def start(self, enable_tiles: bool = False,
                    enable_trust: bool = False) -> None:
        """Start all Keel subsystems."""
        self._running = True

        # Bearing watcher — always on
        self.watcher = BearingWatcher(self.nc)
        await self.watcher.start()

        # Collision detector — always on
        self.collision_detector = CollisionDetector(self.nc)
        await self.collision_detector.start()

        # Tile store — optional, requires JetStream
        if enable_tiles and self.js:
            self.tile_store = TileStore(self.nc, self.js)
            await self.tile_store.create_stream()

        # Trust registry — optional
        if enable_trust:
            self.trust_registry = TrustRegistry(self.nc)
            await self.trust_registry.start()

        logger.info("KeelNATS system started — death is default")

    async def stop(self) -> None:
        """Stop all subsystems. Data dies via TTL."""
        self._running = False

        # Stop agents
        for agent in self.agents.values():
            await agent.stop()

        # Stop watchers
        if self.watcher:
            await self.watcher.stop()
        if self.collision_detector:
            await self.collision_detector.stop()
        if self.trust_registry:
            await self.trust_registry.stop()

        logger.info("KeelNATS system stopped — data will expire via TTL")

    def create_agent(self, agent_id: str,
                     ttl: int = DEFAULT_TTL,
                     position: Optional[tuple[float, float]] = None,
                     velocity: Optional[tuple[float, float]] = None,
                     intention: str = "cruising") -> KeelAgent:
        """Create and register a new Keel agent."""
        pos = Position(*position) if position else Position(
            random.uniform(-10, 10),
            random.uniform(-10, 10),
        )
        vel = Velocity(*velocity) if velocity else Velocity(0, 0)

        heading = Heading(
            agent_id=agent_id,
            position=pos,
            velocity=vel,
            intention=intention,
        )
        agent = KeelAgent(agent_id, self.nc, ttl=ttl, heading=heading)
        self.agents[agent_id] = agent
        return agent


# ─── Utility ────────────────────────────────────────────────────────────────

def random_agent_id(prefix: str = "agent") -> str:
    """Generate a random agent ID."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"
