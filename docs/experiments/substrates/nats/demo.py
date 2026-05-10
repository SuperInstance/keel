"""
demo.py — 3-Agent Keel Demo on NATS

Shows three agents coordinating through NATS:
- Agent Alpha, Bravo, Charlie move through a 2D space
- Bearing watcher computes pairwise bearings
- Collision detector watches for convergence
- All data self-terminates via TTL — no cleanup needed

Run with:
    # Terminal 1: Start NATS server
    nats-server

    # Terminal 2: Run this demo
    python3 demo.py

    # Or from another terminal, watch live:
    nats sub "keel.>" --header

One NATS command to spawn an agent:
    nats reply keel.agent.demo.agent.heading "heading|0.3|0.01" --header "Nats-Msg-Timeout: 30"

One line. One agent. Self-terminating in 30 seconds. No scheduler required.
"""

import asyncio
import json
import logging
import sys
import time
import math

import nats

from keel_nats import (
    KeelNATS,
    KeelAgent,
    CollisionWarning,
    compute_bearing,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-12s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("demo")


# ─── Agent Behaviors ────────────────────────────────────────────────────────


class AgentBehavior:
    """Movement pattern for a demo agent."""

    def __init__(self, agent: KeelAgent):
        self.agent = agent
        self._time = 0.0

    async def update(self, dt: float) -> None:
        self._time += dt
        raise NotImplementedError


class CirclePattern(AgentBehavior):
    """Agent moves in a circle around origin — no collision risk."""

    def __init__(self, agent: KeelAgent, radius: float = 5.0,
                 speed: float = 1.0, phase_offset: float = 0.0):
        super().__init__(agent)
        self.radius = radius
        self.speed = speed
        self.phase = phase_offset

    async def update(self, dt: float) -> None:
        self._time += dt
        self.phase += self.speed * dt / self.radius

        x = self.radius * math.cos(self.phase)
        y = self.radius * math.sin(self.phase)

        vx = -self.speed * math.sin(self.phase)
        vy = self.speed * math.cos(self.phase)

        await self.agent.update_position(x, y)
        await self.agent.update_velocity(vx, vy)


class CrossingPattern(AgentBehavior):
    """Agent crosses through origin at a given angle — creates collision risk."""

    def __init__(self, agent: KeelAgent, angle_deg: float = 0.0,
                 speed: float = 1.5, start_distance: float = 8.0):
        super().__init__(agent)
        self.angle = math.radians(angle_deg)
        self.speed = speed
        self.start_distance = start_distance
        self.distance_traveled = 0.0

    async def update(self, dt: float) -> None:
        self._time += dt
        self.distance_traveled += self.speed * dt

        dist = self.distance_traveled
        x = self.start_distance * math.cos(self.angle) - dist * math.cos(self.angle)
        y = self.start_distance * math.sin(self.angle) - dist * math.sin(self.angle)

        vx = -self.speed * math.cos(self.angle)
        vy = -self.speed * math.sin(self.angle)

        await self.agent.update_position(x, y)
        await self.agent.update_velocity(vx, vy)


# ─── Status Display ─────────────────────────────────────────────────────────


class StatusDisplay:
    """Periodically prints bearing/collision status to console."""

    def __init__(self, watcher, collision):
        self.watcher = watcher
        self.collision = collision

    def render(self) -> str:
        lines = []
        lines.append("─" * 60)
        lines.append(f"  KNOWN AGENTS: {len(self.watcher._headings)}")

        headings = self.watcher._headings
        items = list(headings.items())
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                (a_id, a_h), (b_id, b_h) = items[i], items[j]
                b = compute_bearing(a_h, b_h)
                risk = b.collision_risk
                mark = "⚠️ " if risk > 0.3 else "   "
                lines.append(
                    f"  {mark}{a_id:>10}  x  {b_id:<10}  "
                    f"dist={b.distance:5.2f}  "
                    f"CPA={b.closest_distance:.2f}  "
                    f"t+CPA={b.time_to_closest:5.1f}s  "
                    f"risk={risk:.2f}"
                )

        warnings = self.collision.warnings
        if warnings:
            lines.append("  ── COLLISIONS ──")
            for w in warnings:
                icon = "🔴" if w.warning_level == "critical" else \
                       "🟡" if w.warning_level == "warning" else "🟢"
                lines.append(
                    f"  {icon} {w.agent_a} x {w.agent_b}: "
                    f"risk={w.risk:.2f} impact_t={w.time_to_impact:.1f}s"
                )

        lines.append("─" * 60)
        return "\n".join(lines)

    async def display(self, interval: float = 1.0):
        while True:
            print(self.render())
            await asyncio.sleep(interval)


# ─── Scenario ───────────────────────────────────────────────────────────────


async def run_scenario(nc, js=None):
    """Run the 3-agent Keel demo over NATS."""
    keel = KeelNATS(nc, js)
    await keel.start(enable_tiles=False, enable_trust=False)

    # Create agents
    alpha = keel.create_agent("alpha", ttl=30,
                              position=(5.0, 0.0), velocity=(0.0, 1.0),
                              intention="patrolling")
    bravo = keel.create_agent("bravo", ttl=25,
                              position=(-10.0, 5.0), velocity=(1.5, 0.0),
                              intention="transiting")
    charlie = keel.create_agent("charlie", ttl=20,
                                position=(3.0, -10.0), velocity=(0.0, 1.5),
                                intention="surveying")

    # Assign behaviors
    behaviors = {
        alpha.agent_id: CirclePattern(alpha, radius=6.0, speed=0.8),
        bravo.agent_id: CrossingPattern(bravo, angle_deg=10, speed=1.8,
                                        start_distance=10.0),
        charlie.agent_id: CrossingPattern(charlie, angle_deg=80, speed=1.8,
                                          start_distance=10.0),
    }

    # Status display
    display = StatusDisplay(keel.watcher, keel.collision_detector)

    # Collision callback
    async def on_collision(warning: CollisionWarning):
        icon = "🔴" if warning.warning_level == "critical" else \
               "🟡" if warning.warning_level == "warning" else "🟢"
        print(f"  {icon} COLLISION [{warning.warning_level.upper()}]: "
              f"{warning.agent_a} x {warning.agent_b}  "
              f"ETA={warning.time_to_impact:.1f}s  risk={warning.risk:.2f}")

    keel.collision_detector.on_collision = on_collision

    # Print header
    print()
    print("=" * 60)
    print("  KEEL DEMO — 3 Agents on NATS")
    print("  Death is default. TTL enforces life.")
    print("=" * 60)
    print()
    print("  Agents:")
    for name in ["alpha", "bravo", "charlie"]:
        print(f"    - {name} — TTL={keel.agents[name].ttl}s")
    print()

    # Start agents
    await asyncio.gather(*[a.start() for a in keel.agents.values()])

    # Start display
    display_task = asyncio.create_task(display.display(interval=2.0))

    # Simulation loop
    dt = 0.1
    sim_duration = 20.0
    steps = int(sim_duration / dt)

    try:
        for step in range(steps):
            t = step * dt
            for agent_id, agent in keel.agents.items():
                behavior = behaviors[agent_id]
                await behavior.update(dt)

                if abs(t - 0.0) < 0.01:
                    await agent.set_intention("starting")
                elif abs(t - 5.0) < 0.01:
                    await agent.set_intention("transiting")
                elif abs(t - 10.0) < 0.01:
                    await agent.set_intention("evading" if "bravo" in agent_id
                                              else "transiting")
                elif abs(t - 15.0) < 0.01:
                    await agent.set_intention("returning")

            await asyncio.sleep(dt)

        print("  Simulation complete — 20 seconds elapsed.\n")

    except asyncio.CancelledError:
        print("  Simulation cancelled.\n")
    finally:
        display_task.cancel()
        await keel.stop()


# ─── Main ───────────────────────────────────────────────────────────────────


async def main():
    server = "nats://localhost:4222"
    logger.info(f"Connecting to NATS at {server}...")

    try:
        nc = await nats.connect(server)
        logger.info(f"Connected to NATS ({nc.connected_url})")
    except Exception as e:
        logger.error(f"Cannot connect to NATS: {e}")
        print()
        print("  NATS server not running. Start it with:")
        print()
        print("      nats-server")
        print()
        print("  Then run this demo again.")
        print()
        print("  Or watch live from another terminal:")
        print()
        print("      nats sub 'keel.>' --header")
        print()
        sys.exit(1)

    js = None
    try:
        js = nc.jetstream()
    except Exception:
        pass

    try:
        await run_scenario(nc, js)
    finally:
        await nc.close()
        logger.info("Disconnected from NATS")


if __name__ == "__main__":
    asyncio.run(main())
