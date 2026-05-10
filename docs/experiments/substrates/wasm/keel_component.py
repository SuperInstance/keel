#!/usr/bin/env python3
"""
keel_component.py — WASM Component Stub Generator for Keel TTL Engine

Generates WASM component stubs from the keel.wit interface definition.
Shows how capability-based security maps to trust TTL.

Key insight:
    WASM fuel = lifespan(E) — the energy function of load, time, and use.
    Capability grants = trust TTL — decay over time, bounded by provenance depth.
    Component interface = bearing protocol — agents observe each other through interfaces.

Each component receives exactly the capabilities it needs,
with a fuel budget equal to its lifespan.
"""

import json
import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional, Callable
from enum import Enum

# ─────────────────────────────────────────────
# WIT MODEL — parsed from keel.wit interface
# ─────────────────────────────────────────────


class Risk(Enum):
    STABLE = "stable"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Tile:
    """A tile — the fundamental data structure with a death clock."""
    keel_date: float  # birth timestamp (monotonic ms)
    ttl_ms: float     # time-to-live in milliseconds
    data: str         # payload

    @property
    def is_alive(self) -> bool:
        """Life check: keel_date + ttl_ms > now"""
        return (self.keel_date + self.ttl_ms) > (time.time() * 1000)

    @property
    def remaining_ms(self) -> float:
        """How much life remains (0 if dead)."""
        remaining = (self.keel_date + self.ttl_ms) - (time.time() * 1000)
        return max(0.0, remaining)


@dataclass
class Agent:
    """An agent — a WASM component with lifespan and heading."""
    keel_date: float     # birth
    ttl_ms: float        # lifespan
    last_output: float   # last output timestamp
    heading: str         # current directional intent

    @property
    def is_present(self) -> bool:
        """An agent is present if alive AND active (has produced output)."""
        alive = (self.keel_date + self.ttl_ms) > (time.time() * 1000)
        active = self.last_output > 0
        return alive and active


@dataclass
class Bearing:
    """A bearing — one agent's observation of another, with its own TTL."""
    target: str        # which agent was observed
    angle: float       # relative bearing (radians)
    rate: float        # rate of angle change (rad/s)
    observed: float    # observation timestamp
    ttl_ms: float      # how long this bearing is valid

    @property
    def collision_risk(self) -> Risk:
        """Calculate collision risk from bearing + rate."""
        if not self.is_valid:
            return Risk.STABLE  # stale bearing = no data
        elapsed = (time.time() * 1000) - self.observed
        age_factor = elapsed / self.ttl_ms

        # Rate factor: positive rate means closing angle
        rate_factor = abs(self.rate) / 3.14159  # normalize to π

        composite = age_factor * rate_factor
        if composite > 0.7:
            return Risk.CRITICAL
        elif composite > 0.3:
            return Risk.WARNING
        return Risk.STABLE

    @property
    def is_valid(self) -> bool:
        """Bearing is valid if within its TTL."""
        return (self.observed + self.ttl_ms) > (time.time() * 1000)


@dataclass
class Trust:
    """A trust assertion — confidence in a claim, with provenance depth."""
    assertion: str      # the claim
    confidence: float   # how sure [0.0, 1.0]
    depth: int          # chain length (0=self, 1=direct)
    proven: float       # when verified
    ttl_ms: float       # trust validity period

    @property
    def effective_confidence(self) -> float:
        """
        Effective confidence accounting for TTL decay.

        Formula: confidence * (1 - decay_factor)
        where decay_factor = min(1.0, elapsed / ttl_ms)

        A trust assertion that's 50% expired has 50% effective confidence.
        A fully expired trust has 0% effective confidence.
        """
        elapsed = (time.time() * 1000) - self.proven
        decay_factor = min(1.0, elapsed / self.ttl_ms)
        return self.confidence * (1.0 - decay_factor)


# ─────────────────────────────────────────────
# CAPABILITY MODEL
# ─────────────────────────────────────────────


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
    """A capability — an unforgeable token granting access."""
    name: CapabilityName
    granted_at: float  # when issued
    ttl_ms: float      # validity period

    @property
    def is_expired(self) -> bool:
        """Capabilities decay just like trust TTL."""
        return (self.granted_at + self.ttl_ms) <= (time.time() * 1000)


@dataclass
class FuelBudget:
    """
    Fuel = lifespan(E) — the unified equation.

    Each component has a fuel budget.
    Each invocation consumes fuel.
    When fuel reaches 0, the component is dead.
    No orchestrator killed it. No GC reaped it.
    Death is the default state.
    """
    remaining: float      # remaining fuel units
    per_call_cost: float  # fuel cost per invocation
    calls_budget: int     # max calls before depletion

    @classmethod
    def from_lifespan(cls, lifespan_ms: float, call_cost: float = 1.0):
        """Create a fuel budget from a lifespan in milliseconds."""
        calls = int(lifespan_ms / call_cost) if call_cost > 0 else 0
        return cls(
            remaining=float(lifespan_ms),
            per_call_cost=call_cost,
            calls_budget=calls,
        )

    def consume(self, cost: Optional[float] = None) -> bool:
        """Consume fuel. Returns False if already dead."""
        cost = cost or self.per_call_cost
        if self.remaining <= 0:
            return False
        self.remaining -= cost
        self.calls_budget -= 1
        return self.remaining > 0 and self.calls_budget > 0

    @property
    def is_depleted(self) -> bool:
        """Fuel depleted = component is dead. Death is default."""
        return self.remaining <= 0 or self.calls_budget <= 0


# ─────────────────────────────────────────────
# COMPONENT STUB
# ─────────────────────────────────────────────


class WasmComponent:
    """
    Base class for all Keel WASM components.

    This mirrors the `world keel-agent` in keel.wit.
    Each component receives capabilities and fuel on creation.
    """

    def __init__(
        self,
        name: str,
        fuel_budget: FuelBudget,
        capabilities: list[Capability],
        behavior: Optional[Callable] = None,
    ):
        self.name = name
        self.fuel = fuel_budget
        self.capabilities = {c.name: c for c in capabilities}
        self.created_at = time.time() * 1000
        self.last_output = 0.0
        self.heading = "idle"
        self.behavior = behavior
        self.log: list[str] = []

    @property
    def has_fuel(self) -> bool:
        """A component with no fuel is dead. Death is default."""
        return not self.fuel.is_depleted

    def has_capability(self, name: CapabilityName) -> bool:
        """Check capability possession (and expiration)."""
        cap = self.capabilities.get(name)
        if cap is None:
            return False
        if cap.is_expired:
            # Capabilities decay like trust TTL — auto-revoke on expiry
            del self.capabilities[name]
            return False
        return True

    def run(self) -> str:
        """
        Component entry point. Consumes fuel on each call.
        Returns the component's output as a string.

        This is the `run: func() -> string` export from keel.wit.
        """
        if not self.fuel.consume():
            # Death is default — no fuel = no execution
            return f"COMPONENT_DEAD:{self.name}"

        # Grant the component access to its capabilities
        output = self.execute()
        self.last_output = time.time() * 1000
        return output

    def execute(self) -> str:
        """
        Override this in subclasses, or set behavior= on construction.
        This is where the agent's actual logic lives.
        Capabilities are checked before any resource access.
        """
        if self.behavior:
            return self.behavior(self)
        return f"{self.name}:executed (no behavior set)"

    def __repr__(self) -> str:
        return (f"WasmComponent({self.name}, fuel={self.fuel.remaining:.1f}, "
                f"capabilities={len(self.capabilities)}, "
                f"heading='{self.heading}')")


# ─────────────────────────────────────────────
# COMPONENT GENERATOR
# ─────────────────────────────────────────────


def generate_component_stub(
    name: str,
    lifespan_ms: float,
    capabilities: list[CapabilityName],
    per_call_cost: float = 1.0,
) -> WasmComponent:
    """
    Generate a WASM component stub from the WIT interface.

    This is the primary factory function. It creates a component
    with a fuel budget = lifespan, and grants exactly the requested
    capabilities.

    Capability grants ARE trust TTL — they decay, must be renewed,
    are bounded by depth. The component receives NO ambient authority.
    """
    fuel = FuelBudget.from_lifespan(lifespan_ms, per_call_cost)
    caps = [
        Capability(
            name=cap,
            granted_at=time.time() * 1000,
            ttl_ms=lifespan_ms,  # capabilities live as long as the agent
        )
        for cap in capabilities
    ]

    component = WasmComponent(name, fuel, caps)

    # Record the generation
    component.log.append(
        f"GENERATED:{name} lifespan={lifespan_ms}ms "
        f"fuel={fuel.remaining} caps={[c.name.value for c in caps]}"
    )

    return component


def print_component_manifest(component: WasmComponent) -> str:
    """Print a WIT-style manifest for the component."""
    lines = [
        f"// Component: {component.name}",
        f"// Package: keel:ttl/component@{component.name}",
        f"//",
        f"// Fuel (lifespan): {component.fuel.remaining:.1f} units",
        f"// Per-call cost:  {component.fuel.per_call_cost}",
        f"// Calls budget:   {component.fuel.calls_budget}",
        f"// Capabilities:   {component.fuel.calls_budget}",
    ]
    for cap in component.capabilities.values():
        lines.append(f"//   - {cap.name.value} (TTL: {cap.ttl_ms}ms)")
    lines.append("//")
    lines.append("world keel-agent {")
    lines.append("    import keel-ttl;")
    lines.append("    import fuel-budget;")
    lines.append("    import capability-store;")
    lines.append("    import plato-storage;")
    lines.append("    export run: func() -> string;")
    lines.append("}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# DEMO
# ─────────────────────────────────────────────


if __name__ == "__main__":
    print("=" * 60)
    print("Keel TTL Engine — WASM Component Generator")
    print("=" * 60)
    print()
    print("Fuel = lifespan(E). Death is default.")
    print("Capabilities = trust TTL. Decay is automatic.")
    print()

    # Create a navigator agent with specific capabilities
    navigator = generate_component_stub(
        name="navigator-v1",
        lifespan_ms=30_000,  # 30 second lifespan
        capabilities=[
            CapabilityName.READ_HEADING,
            CapabilityName.WRITE_TILE,
            CapabilityName.HEARTBEAT,
        ],
        per_call_cost=5.0,
    )

    print("── Component: navigator-v1 ──")
    print(print_component_manifest(navigator))
    print()

    # Create a scout agent (fewer capabilities, shorter lifespan)
    scout = generate_component_stub(
        name="scout-alpha",
        lifespan_ms=10_000,  # 10 second lifespan — scouts are short-lived
        capabilities=[
            CapabilityName.READ_HEADING,
            CapabilityName.HEARTBEAT,
        ],
        per_call_cost=2.0,
    )

    print("── Component: scout-alpha ──")
    print(print_component_manifest(scout))
    print()

    # Demonstrate fuel depletion
    print("── Demonstrating fuel depletion (death is default) ──")
    print(f"navigator fuel before: {navigator.fuel.remaining}")
    result = navigator.run()
    print(f"navigator run: {result}")
    print(f"navigator fuel after: {navigator.fuel.remaining}")
    print()

    # Demonstrate capability expiry
    print("── Demonstrating capability TTL decay ──")
    tile_data = Tile(
        keel_date=time.time() * 1000,
        ttl_ms=5_000,  # 5 second tile
        data="{'heading': 120, 'speed': 8}",
    )
    print(f"Tile ttl: {tile_data.ttl_ms}ms")
    print(f"Tile alive: {tile_data.is_alive}")
    print(f"Tile remaining: {tile_data.remaining_ms:.1f}ms")
    print()

    # Demonstrate trust decay
    trust = Trust(
        assertion="heading=120",
        confidence=0.95,
        depth=1,
        proven=time.time() * 1000 - 3_000,  # 3 seconds ago
        ttl_ms=5_000,  # valid for 5 seconds
    )
    print(f"Trust assertion: '{trust.assertion}'")
    print(f"Raw confidence: {trust.confidence}")
    print(f"Effective confidence (60% expired): {trust.effective_confidence:.3f}")
    print()

    # Demonstrate bearing collision risk
    print("── Bearing collision risk ──")
    closing_bearing = Bearing(
        target="obstacle-01",
        angle=0.05,       # almost head-on (radians)
        rate=0.5,         # closing fast (rad/s)
        observed=time.time() * 1000 - 500,  # 500ms ago
        ttl_ms=2_000,    # valid for 2 seconds
    )
    print(f"Bearing to: {closing_bearing.target}")
    print(f"Risk: {closing_bearing.collision_risk.value}")
    print()

    print("─" * 60)
    print("KEY INSIGHT: WASM Component Model IS Keel Architecture")
    print("─" * 60)
    print("1. Components = agents with bounded lifespan")
    print("2. Fuel = lifespan(E) — unified energy equation")
    print("3. Capabilities = trust TTL — decay, renewal, depth")
    print("4. Interface = bearing protocol — observation through WIT")
    print("5. Death is default — no fuel = no execution")
    print("=" * 60)
