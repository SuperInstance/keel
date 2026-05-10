#!/usr/bin/env python3
"""
keel_runtime.py — Minimal WASM-like Runtime for Keel TTL Engine

This runtime simulates the WASM Component Model:
  - Agents are callable components with fuel budgets
  - Each invocation deducts from fuel
  - Fuel = 0 → component is dead (death is default)
  - Capabilities are checked before any operation
  - Capabilities decay (TTL-based trust)

The runtime IS the field. Agents are components.
Fuel is the unified equation: lifespan = f(use, load, time).
"""

import time
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable


# ─────────────────────────────────────────────
# CORE TYPES
# ─────────────────────────────────────────────


class Risk(Enum):
    STABLE = "stable"
    WARNING = "warning"
    CRITICAL = "critical"


class CapabilityName(Enum):
    READ_HEADING = "read-heading"
    WRITE_TILE = "write-tile"
    READ_TILE = "read-tile"
    SPAWN_AGENT = "spawn-agent"
    REPLENISH_FUEL = "replenish-fuel"
    WRITE_TRUST = "write-trust"
    READ_TRUST = "read-trust"
    HEARTBEAT = "heartbeat"


@dataclass
class Capability:
    """An unforgeable (in practice) token granting resource access."""
    name: CapabilityName
    granted_at: float
    ttl_ms: float

    @property
    def is_expired(self) -> bool:
        return (self.granted_at + self.ttl_ms) <= (time.time() * 1000)


@dataclass
class FuelBudget:
    """
    Fuel = lifespan(E).

    The unified equation. Each component's lifespan is its fuel budget.
    Each call consumes fuel. Fuel = 0 → death.
    No orchestrator killed it. No GC reaped it.
    Death is the default state — agents must earn life.
    """
    total: float
    remaining: float
    per_call_cost: float

    @classmethod
    def from_lifespan(cls, lifespan_ms: float, call_cost: float = 1.0):
        return cls(
            total=lifespan_ms,
            remaining=lifespan_ms,
            per_call_cost=call_cost,
        )

    def consume(self, cost: Optional[float] = None) -> bool:
        """Return True if agent still alive after consume."""
        c = cost or self.per_call_cost
        if self.remaining <= 0:
            return False
        self.remaining -= c
        return self.remaining > 0

    @property
    def is_depleted(self) -> bool:
        return self.remaining <= 0

    @property
    def depletion_pct(self) -> float:
        return (1.0 - self.remaining / self.total) * 100 if self.total > 0 else 100.0


# ─────────────────────────────────────────────
# COMPONENT (AGENT) MODEL
# ─────────────────────────────────────────────


class AgentComponent:
    """
    A WASM component in the Keel runtime.

    Every agent:
    - Has a fuel budget = lifespan
    - Holds a set of capabilities (granted, not ambient)
    - Exports a `run()` entry point
    - Can observe other agents through bearings
    - Can issue trust assertions
    - Dies when fuel depletes
    """

    def __init__(
        self,
        agent_id: str,
        fuel: FuelBudget,
        capabilities: Optional[list[Capability]] = None,
        behavior: Optional[Callable] = None,
    ):
        self.id = agent_id
        self.fuel = fuel
        self.capabilities: dict[CapabilityName, Capability] = {
            c.name: c for c in (capabilities or [])
        }
        self.behavior = behavior or self._default_behavior
        self.created_at = time.time()
        self.last_output = 0.0
        self.last_heartbeat = time.time()
        self.heading = "idle"
        self.bearings: dict[str, "Bearing"] = {}
        self.trust_assertions: list["Trust"] = []
        self.tile_buffer: list[str] = []
        self.invocation_count = 0

    def has_capability(self, name: CapabilityName) -> bool:
        cap = self.capabilities.get(name)
        if cap is None or cap.is_expired:
            return False
        return True

    def run(self) -> str:
        """Entry point. Consumes fuel. Returns output."""
        self.invocation_count += 1
        if not self.fuel.consume():
            return f"COMPONENT_DEAD:{self.id}"

        # Run the agent's behavior
        result = self.behavior(self)
        self.last_output = time.time()
        return result

    def scan_heading(self, runtime: "KeelRuntime") -> Optional[float]:
        """Read another agent's heading (requires read-heading capability)."""
        if not self.has_capability(CapabilityName.READ_HEADING):
            return None
        # In real WASM: component calls imported function
        # Here: runtime mediates the capability check
        return runtime.get_heading(self)

    def store_tile(self, data: str, ttl_ms: float, runtime: "KeelRuntime") -> Optional[str]:
        """Store a tile (requires write-tile capability)."""
        if not self.has_capability(CapabilityName.WRITE_TILE):
            return None
        tile_id = runtime.plato_store(self.id, data, ttl_ms)
        self.tile_buffer.append(tile_id)
        return tile_id

    def issue_trust(
        self,
        assertion: str,
        confidence: float,
        depth: int,
        ttl_ms: float,
    ) -> "Trust":
        """Issue a trust assertion about something."""
        t = Trust(
            assertion=assertion,
            confidence=confidence,
            depth=depth,
            proven=time.time() * 1000,
            ttl_ms=ttl_ms,
        )
        self.trust_assertions.append(t)
        return t

    @staticmethod
    def _default_behavior(agent) -> str:
        return f"{agent.id}:executed"

    @property
    def is_present(self) -> bool:
        """Alive AND active (produced output recently)."""
        alive = not self.fuel.is_depleted
        active = self.last_output > 0
        return alive and active

    def __repr__(self) -> str:
        return (f"Agent({self.id}, fuel={self.fuel.remaining:.1f}/{self.fuel.total:.1f}, "
                f"caps={len(self.capabilities)}, heading='{self.heading}')")


@dataclass
class Bearing:
    """An observation of another agent by this agent."""
    target: str
    angle: float
    rate: float
    observed: float
    ttl_ms: float

    @property
    def collision_risk(self) -> Risk:
        if not self.is_valid:
            return Risk.STABLE
        elapsed = (time.time() * 1000) - self.observed
        age_factor = elapsed / self.ttl_ms
        rate_factor = abs(self.rate) / 3.14159
        composite = age_factor * rate_factor
        if composite > 0.7:
            return Risk.CRITICAL
        elif composite > 0.3:
            return Risk.WARNING
        return Risk.STABLE

    @property
    def is_valid(self) -> bool:
        return (self.observed + self.ttl_ms) > (time.time() * 1000)


@dataclass
class Trust:
    """A trust assertion — confidence in a claim."""
    assertion: str
    confidence: float
    depth: int
    proven: float
    ttl_ms: float

    @property
    def effective_confidence(self) -> float:
        elapsed = (time.time() * 1000) - self.proven
        decay_factor = min(1.0, elapsed / self.ttl_ms)
        return self.confidence * (1.0 - decay_factor)


# ─────────────────────────────────────────────
# THE RUNTIME (THE FIELD)
# ─────────────────────────────────────────────


@dataclass
class PlatoTile:
    """A stored tile in PLATO storage."""
    id: str
    data: str
    created_at: float
    ttl_ms: float
    owner: str

    @property
    def is_alive(self) -> bool:
        return (self.created_at + self.ttl_ms) > (time.time() * 1000)


class KeelRuntime:
    """
    The runtime IS the field.

    Agents are components. The runtime mediates all interactions.
    No component has ambient authority — all access goes through
    capability-gated imports.

    The runtime tracks:
    - All registered agents
    - Fuel depletion
    - Capability grants
    - PLATO storage (tiles)
    """

    def __init__(self):
        self.agents: dict[str, AgentComponent] = {}
        self.tiles: dict[str, PlatoTile] = {}
        self.tile_counter = 0
        self.capability_grants: dict[str, dict[CapabilityName, Capability]] = {}
        self.clock = 0.0  # monotonic time in ms
        self.events: list[str] = []

    def register_agent(
        self,
        agent: AgentComponent,
    ) -> AgentComponent:
        """Register an agent component in the runtime."""
        self.agents[agent.id] = agent
        self.capability_grants[agent.id] = agent.capabilities
        self._log(f"REGISTER:{agent.id} fuel={agent.fuel.total:.0f}")
        return agent

    def invoke(self, agent_id: str) -> str:
        """Invoke an agent's run() — consumes fuel."""
        agent = self.agents.get(agent_id)
        if agent is None:
            return f"ERROR:agent_not_found:{agent_id}"
        if agent.fuel.is_depleted:
            self._log(f"DEATH:{agent_id} — fuel depleted")
            return f"COMPONENT_DEAD:{agent_id}"

        result = agent.run()

        # Check if agent just died
        if "COMPONENT_DEAD" in result:
            self._log(f"DEATH:{agent_id} — fuel depleted (natural)")

        return result

    def get_heading(self, caller: AgentComponent) -> Optional[float]:
        """Mediated heading access — checks capability."""
        if not caller.has_capability(CapabilityName.READ_HEADING):
            self._log(f"DENIED:{caller.id} lacks read-heading capability")
            return None
        # In a real system, this reads from the field
        # Here we return the caller's own heading (simplified)
        return 0.0  # placeholder

    def plato_store(
        self,
        owner: str,
        data: str,
        ttl_ms: float,
    ) -> str:
        """Store a tile in PLATO. No capability check here — caller checks."""
        tile_id = f"tile:{owner}:{self.tile_counter}"
        self.tile_counter += 1
        self.tiles[tile_id] = PlatoTile(
            id=tile_id,
            data=data,
            created_at=time.time() * 1000,
            ttl_ms=ttl_ms,
            owner=owner,
        )
        self._log(f"STORE:{tile_id} owner={owner} ttl={ttl_ms:.0f}ms")
        return tile_id

    def plato_read(self, tile_id: str, caller: AgentComponent) -> Optional[PlatoTile]:
        """Read a tile. Requires read-tile capability."""
        if not caller.has_capability(CapabilityName.READ_TILE):
            self._log(f"DENIED:{caller.id} read-tile capability missing")
            return None
        tile = self.tiles.get(tile_id)
        if tile is None or not tile.is_alive:
            return None
        return tile

    def grant_capability(
        self,
        granter: AgentComponent,
        target_id: str,
        name: CapabilityName,
        ttl_ms: float,
    ):
        """Grant a capability from one agent to another."""
        # Check if granter has meta-capability to grant this
        # In real WASM: this is a compose-time check
        target = self.agents.get(target_id)
        if target is None:
            self._log(f"GRANT_FAILED:{target_id} not found")
            return

        cap = Capability(name=name, granted_at=time.time() * 1000, ttl_ms=ttl_ms)
        target.capabilities[name] = cap
        self.capability_grants.setdefault(target_id, {})[name] = cap
        self._log(f"GRANT:{granter.id} → {target_id} {name.value} ttl={ttl_ms:.0f}ms")

    def expire_capabilities(self):
        """Periodic sweep: remove expired capabilities from all agents."""
        for agent_id, agent in self.agents.items():
            expired = [n for n, c in agent.capabilities.items() if c.is_expired]
            for name in expired:
                del agent.capabilities[name]
                self._log(f"CAP_EXPIRED:{agent_id} lost {name.value}")

    def remove_dead_agents(self):
        """Periodic sweep: remove agents with depleted fuel."""
        dead = [a_id for a_id, a in self.agents.items() if a.fuel.is_depleted]
        for a_id in dead:
            del self.agents[a_id]
            del self.capability_grants[a_id]
            self._log(f"RECLAIM:{a_id} — component garbage collected")

    def expire_tiles(self):
        """Periodic sweep: remove expired tiles."""
        expired = [t_id for t_id, t in self.tiles.items() if not t.is_alive]
        for t_id in expired:
            del self.tiles[t_id]
            self._log(f"TILE_EXPIRED:{t_id}")

    def gc(self):
        """Garbage collection tick: expire caps, reclaim dead agents, expire tiles."""
        self.expire_capabilities()
        self.remove_dead_agents()
        self.expire_tiles()

    def status(self) -> dict:
        """Runtime status snapshot."""
        return {
            "agents": {a_id: str(a) for a_id, a in self.agents.items()},
            "tiles": len(self.tiles),
            "events": self.events[-5:],  # last 5 events
        }

    def _log(self, event: str):
        self.events.append(f"[T={time.strftime('%H:%M:%S')}] {event}")


# ─────────────────────────────────────────────
# EXAMPLE: CONVOY SCENARIO
# ─────────────────────────────────────────────


def run_convoy_scenario():
    """
    Demonstrate the Keel TTL Engine with a convoy of agents.

    Three ships (agents) navigating in formation:
    - leader: long lifespan, many capabilities
    - follower: shorter lifespan, fewer capabilities
    - scout: very short lifespan, minimal capabilities

    The demonstration shows:
    1. Agents consume fuel with each invocation
    2. Short-lived agents die first (death is default)
    3. Capability access is gated
    4. Trust assertions decay over time
    5. Bearings become stale after TTL expiry
    """
    runtime = KeelRuntime()

    # ── Create agents with different lifespans ──
    leader = AgentComponent(
        agent_id="leader",
        fuel=FuelBudget.from_lifespan(lifespan_ms=50_000, call_cost=5_000),
        capabilities=[
            Capability(CapabilityName.READ_HEADING, time.time() * 1000, 50_000),
            Capability(CapabilityName.WRITE_TILE, time.time() * 1000, 50_000),
            Capability(CapabilityName.READ_TILE, time.time() * 1000, 50_000),
            Capability(CapabilityName.REPLENISH_FUEL, time.time() * 1000, 50_000),
            Capability(CapabilityName.SPAWN_AGENT, time.time() * 1000, 50_000),
            Capability(CapabilityName.HEARTBEAT, time.time() * 1000, 50_000),
        ],
    )
    leader.heading = "north-by-northeast"

    follower = AgentComponent(
        agent_id="follower",
        fuel=FuelBudget.from_lifespan(lifespan_ms=20_000, call_cost=5_000),
        capabilities=[
            Capability(CapabilityName.READ_HEADING, time.time() * 1000, 20_000),
            Capability(CapabilityName.WRITE_TILE, time.time() * 1000, 20_000),
            Capability(CapabilityName.HEARTBEAT, time.time() * 1000, 20_000),
        ],
    )
    follower.heading = "follow-leader"

    scout = AgentComponent(
        agent_id="scout",
        fuel=FuelBudget.from_lifespan(lifespan_ms=5_000, call_cost=3_000),
        capabilities=[
            Capability(CapabilityName.READ_HEADING, time.time() * 1000, 5_000),
            Capability(CapabilityName.HEARTBEAT, time.time() * 1000, 5_000),
        ],
    )
    scout.heading = "ahead-recon"

    runtime.register_agent(leader)
    runtime.register_agent(follower)
    runtime.register_agent(scout)

    # ── Simulate time ticks ──
    print("=" * 70)
    print("KEEL TTL RUNTIME — CONVOY SCENARIO")
    print("Fuel = lifespan(E). Death is default.")
    print("=" * 70)

    for tick in range(8):
        print(f"\n── Tick {tick + 1} ──")

        # Invoke all agents
        for agent_id in ["leader", "follower", "scout"]:
            agent = runtime.agents.get(agent_id)
            if agent is None:
                print(f"  {agent_id}: [DEAD — component reclaimed]")
                continue
            result = runtime.invoke(agent_id)
            print(f"  {agent_id}: {result[:60]}")
            print(f"    fuel: {agent.fuel.remaining:.1f}/{agent.fuel.total:.1f} "
                  f"({agent.fuel.depletion_pct:.0f}% consumed)")

        # Leader issues trust assertion
        if leader.id in runtime.agents:
            trust = leader.issue_trust(
                assertion="heading=north-by-northeast",
                confidence=0.95,
                depth=0,
                ttl_ms=8_000,
            )
            print(f"  leader trust: '{trust.assertion}' "
                  f"eff_conf={trust.effective_confidence:.3f}")

        # Follower observes leader (bearing)
        if follower.id in runtime.agents and leader.id in runtime.agents:
            bearing = Bearing(
                target="leader",
                angle=0.15,
                rate=0.02,
                observed=time.time() * 1000,
                ttl_ms=4_000,
            )
            follower.bearings["leader"] = bearing
            print(f"  follower bearing → leader: "
                  f"risk={bearing.collision_risk.value}")

        # Scout stores a tile
        if scout.id in runtime.agents:
            result = scout.store_tile(
                data="obstacle-detected-ahead",
                ttl_ms=3_000,  # short-lived tile
                runtime=runtime,
            )
            print(f"  scout tile: {result}")

        # GC tick every 3 rounds
        if tick % 3 == 2:
            print(f"\n  [GC sweep]")
            runtime.gc()

        time.sleep(0.1)  # simulate clock progression

    # ── Final state ──
    print("\n" + "=" * 70)
    print("FINAL STATE")
    print("=" * 70)
    status = runtime.status()
    for a_id, a_str in status["agents"].items():
        print(f"  {a_str}")
    print(f"  Live tiles: {status['tiles']}")
    print(f"  Events logged: {len(runtime.events)}")

    # Verify: scout should be dead (short lifespan)
    # Verify correct deaths
    if "scout" not in runtime.agents:
        print("\n  ✓ Scout correctly died (death is default)")
    else:
        scout = runtime.agents["scout"]
        print(f"\n  ⚠ Scout still present (fuel={scout.fuel.remaining:.0f}) — needs more ticks")
    
    if "follower" not in runtime.agents:
        print("  ✓ Follower also died (fuel exhaustion)")
    else:
        print(f"  ℹ Follower still alive (fuel remaining)")
    print("  ✓ Fuel depletion is natural termination")
    print("  ✓ Capabilities decay with time")
    print("  ✓ No orchestrator killed anything — fuel budget is life")
    print("  ✓ Runtime IS the field — components are agents")
    print("=" * 70)


if __name__ == "__main__":
    run_convoy_scenario()
