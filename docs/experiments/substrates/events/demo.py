#!/usr/bin/env python3
"""
demo.py — Keel Event Sourcing Demo

Replay 50 events through the field and show the current projected state.
Demonstrates that:
  - Events are the only truth
  - Projections derive current state
  - TTL expiry is computed, not stored
  - Death is the absence of later events
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from keel_events import (
    EventStore,
    TileCreated,
    TaskCreated,
    TaskStepCompleted,
    AgentSpawned,
    AgentHeartbeat,
    BearingObserved,
    TrustAsserted,
    TrustDecayed,
    Field,
    FrozenTime,
)


def make_event_set(time: FrozenTime) -> EventStore:
    """
    Create a scenario with 50 events simulating a fleet operation.
    
    Timeline (all times relative to t=0):
      0s  - 2 tiles created (hull, engine)
     10s  - 3 agents spawned (navigator, engineer, pilot)
     20s  - task: "Refit engine" created (3 steps, 60s TTL)
     30s  - navigator observes 2 bearings
     40s  - pilot observes 1 bearing  
     50s  - trust asserted: navigator trusts pilot
     55s  - task step 1 completed
     60s  - agent heartbeats from navigator and pilot
     70s  - task step 2 completed
     80s  - trust decayed (confidence drops)
     90s  - agent heartbeat from engineer only
    100s  - task step 3 completed → task complete
    110s  - last heartbeat from... let's design this right
    """
    store = EventStore()
    
    # We'll build 50 events following a realistic fleet scenario
    # Generation events (tiles, agents, tasks) + operation events (bearings, trust, heartbeats, steps)
    
    # ── Phase 1: Foundation — Tiles ──
    store.append(TileCreated(
        tile_id="tile-hull-001",
        keel_date=time.now(),
        ttl=120.0,  # 2 minute TTL
        tile_type="hull",
        data={"class": "A", "displacement": "40 tons"},
    ))
    
    store.append(TileCreated(
        tile_id="tile-engine-001",
        keel_date=time.now(),
        ttl=200.0,  # 200s TTL
        tile_type="engine",
        data={"type": "diesel", "hp": 350},
    ))
    
    # ── Phase 2: Crew — Agents ──
    store.append(AgentSpawned(
        agent_id="agent-navigator",
        keel_date=time.now(),
        ttl=60.0,  # 60s TTL
        heading="Scan and survey",
        spawner_id="system",
    ))
    
    store.append(AgentSpawned(
        agent_id="agent-engineer",
        keel_date=time.now(),
        ttl=90.0,
        heading="Engine maintenance",
        spawner_id="system",
    ))
    
    store.append(AgentSpawned(
        agent_id="agent-pilot",
        keel_date=time.now(),
        ttl=75.0,
        heading="Navigation and steering",
        spawner_id="system",
    ))
    
    # ── Phase 3: Objectives — Tasks ──
    store.append(TaskCreated(
        task_id="task-refit-001",
        created=time.now(),
        ttl=60.0,
        description="Complete engine refit",
        steps=["Remove old parts", "Install new parts", "Test systems"],
    ))
    
    store.append(TaskCreated(
        task_id="task-survey-001",
        created=time.now(),
        ttl=30.0,  # short TTL — will expire
        description="Survey fishing grounds",
        steps=["Deploy sonar", "Log readings"],
    ))
    
    # ── Phase 4: Observations — Bearings ──
    store.append(BearingObserved(
        observer="agent-navigator",
        target="tile-hull-001",
        angle=45.0,
        rate=0.5,
        observed_at=time.now(),
    ))
    
    store.append(BearingObserved(
        observer="agent-navigator",
        target="tile-engine-001",
        angle=90.0,
        rate=0.2,
        observed_at=time.now(),
    ))
    
    store.append(BearingObserved(
        observer="agent-pilot",
        target="tile-hull-001",
        angle=10.0,
        rate=1.0,
        observed_at=time.now(),
    ))
    
    # ── Phase 5: Trust ──
    store.append(TrustAsserted(
        subject="agent-navigator",
        claim="agent-engineer",
        confidence=0.95,
        depth=1,
        asserted_at=time.now(),
    ))
    
    store.append(TrustAsserted(
        subject="agent-navigator",
        claim="agent-pilot",
        confidence=0.80,
        depth=1,
        asserted_at=time.now(),
    ))
    
    store.append(TrustAsserted(
        subject="system",
        claim="agent-navigator",
        confidence=0.99,
        depth=0,
        asserted_at=time.now(),
    ))
    
    # ── Phase 6: Progress — Task Steps + Heartbeats ──
    store.append(TaskStepCompleted(
        task_id="task-refit-001",
        step_index=0,  # "Remove old parts"
        completed_at=time.now(),
    ))
    
    store.append(TaskStepCompleted(
        task_id="task-refit-001",
        step_index=1,  # "Install new parts"
        completed_at=time.now(),
    ))
    
    # Heartbeats from active agents
    store.append(AgentHeartbeat(
        agent_id="agent-navigator",
        timestamp=time.now(),
    ))
    
    store.append(AgentHeartbeat(
        agent_id="agent-engineer",
        timestamp=time.now(),
    ))
    
    store.append(AgentHeartbeat(
        agent_id="agent-pilot",
        timestamp=time.now(),
    ))
    
    # ── Phase 7: Trust Decay + More Progress ──
    store.append(TrustDecayed(
        subject="agent-navigator",
        claim="agent-engineer",
        new_confidence=0.85,  # decayed from 0.95
    ))
    
    store.append(TaskStepCompleted(
        task_id="task-refit-001",
        step_index=2,  # "Test systems" — task now complete!
        completed_at=time.now(),
    ))
    
    # ── Phase 8: More Heartbeats (pilot stops heartbeating!) ──
    store.append(AgentHeartbeat(
        agent_id="agent-navigator",
        timestamp=time.now(),
    ))
    
    store.append(AgentHeartbeat(
        agent_id="agent-engineer",
        timestamp=time.now(),
    ))
    # agent-pilot stops sending heartbeats here
    
    # ── Phase 9: Second survey bearing ──
    store.append(BearingObserved(
        observer="agent-navigator",
        target="tile-engine-001",
        angle=88.0,  # slight drift
        rate=0.1,
        observed_at=time.now(),
    ))
    
    # ── Phase 10: Extra events to hit 50 ──
    # Create a few more tiles, tasks, and agents to demonstrate expiry
    
    # Another tile (long TTL)
    store.append(TileCreated(
        tile_id="tile-keel-001",
        keel_date=time.now(),
        ttl=180.0,
        tile_type="keel",
        data={"material": "steel", "length": "60 ft"},
    ))
    
    # A tile that was created early but still alive (TTL not yet expired because time is frozen)
    store.append(TileCreated(
        tile_id="tile-deck-001",
        keel_date=time.now(),
        ttl=150.0,
        tile_type="deck",
        data={"material": "teak"},
    ))
    
    # A task with very short TTL — will expire if time advanced
    store.append(TaskCreated(
        task_id="task-urgent-001",
        created=time.now(),
        ttl=5.0,
        description="Critical fix (short deadline)",
        steps=["Fix leak"],
    ))
    
    # Another agent (short TTL, will expire)
    store.append(AgentSpawned(
        agent_id="agent-scout",
        keel_date=time.now(),
        ttl=10.0,
        heading="Scout ahead",
        spawner_id="agent-navigator",
    ))
    
    store.append(AgentHeartbeat(
        agent_id="agent-scout",
        timestamp=time.now(),
    ))
    
    # Extra bearings for fleet awareness
    store.append(BearingObserved(
        observer="agent-engineer",
        target="tile-engine-001",
        angle=0.0,
        rate=0.0,
        observed_at=time.now(),
    ))
    
    store.append(BearingObserved(
        observer="agent-engineer",
        target="tile-hull-001",
        angle=180.0,
        rate=0.0,
        observed_at=time.now(),
    ))
    
    # More trust assertions
    store.append(TrustAsserted(
        subject="agent-pilot",
        claim="agent-navigator",
        confidence=0.70,
        depth=2,
        asserted_at=time.now(),
    ))
    
    store.append(TrustAsserted(
        subject="agent-engineer",
        claim="system",
        confidence=1.0,
        depth=0,
        asserted_at=time.now(),
    ))
    
    # Additional agent with very short TTL
    store.append(AgentSpawned(
        agent_id="agent-herald",
        keel_date=time.now(),
        ttl=3.0,
        heading="Announce status",
        spawner_id="system",
    ))
    
    # Another bearing
    store.append(BearingObserved(
        observer="agent-scout",
        target="tile-keel-001",
        angle=270.0,
        rate=-0.3,
        observed_at=time.now(),
    ))
    
    # Final trust decay
    store.append(TrustDecayed(
        subject="agent-pilot",
        claim="agent-navigator",
        new_confidence=0.55,
    ))
    
    # Create a couple more events to ensure we have enough
    store.append(TaskCreated(
        task_id="task-log-001",
        created=time.now(),
        ttl=100.0,
        description="Log navigation data",
        steps=["Collect data", "Write log"],
    ))
    
    store.append(TaskStepCompleted(
        task_id="task-log-001",
        step_index=0,
        completed_at=time.now(),
    ))
    
    # Last heartbeat from engineer — navigator and pilot have stopped
    store.append(AgentHeartbeat(
        agent_id="agent-engineer",
        timestamp=time.now(),
    ))
    
    # One more trust for the road
    store.append(TrustAsserted(
        subject="system",
        claim="agent-engineer",
        confidence=0.90,
        depth=0,
        asserted_at=time.now(),
    ))
    
    return store


def main() -> None:
    print("=" * 72)
    print("KEEL TTL ENGINE — Event Sourcing Demo")
    print("=" * 72)
    print()
    
    # Create frozen time at epoch (deterministic)
    base_time = 1000000.0
    time_real = FrozenTime(base_time)
    
    # We need to patch the global time so events get realistic timestamps
    # We'll build events with the frozen time
    store = EventStore()
    
    # Replace _now references with our frozen time
    import keel_events as ke
    original_now = ke._now
    ke._now = time_real.now
    
    # ── Build the scenario ──
    # Phase 1: Foundation
    t = base_time
    
    def emit(event_cls, **kwargs):
        kwargs.setdefault("timestamp", time_real.now())
        e = event_cls(**kwargs)
        store.append(e)
        return e
    
    # Phase 1: Tiles
    emit(TileCreated, tile_id="tile-hull-001", keel_date=t, ttl=120.0, tile_type="hull", data={"class": "A"})
    emit(TileCreated, tile_id="tile-engine-001", keel_date=t, ttl=200.0, tile_type="engine", data={"type": "diesel"})
    emit(TileCreated, tile_id="tile-keel-001", keel_date=t, ttl=180.0, tile_type="keel", data={"material": "steel"})
    emit(TileCreated, tile_id="tile-deck-001", keel_date=t, ttl=150.0, tile_type="deck", data={"material": "teak"})
    
    # Phase 2: Agents spawned
    t += 10.0
    time_real.advance(10.0)
    emit(AgentSpawned, agent_id="agent-navigator", keel_date=t, ttl=60.0, heading="Scan and survey", spawner_id="system")
    emit(AgentSpawned, agent_id="agent-engineer", keel_date=t, ttl=90.0, heading="Engine maintenance", spawner_id="system")
    emit(AgentSpawned, agent_id="agent-pilot", keel_date=t, ttl=75.0, heading="Navigation", spawner_id="system")
    emit(AgentSpawned, agent_id="agent-scout", keel_date=t, ttl=10.0, heading="Scout ahead", spawner_id="agent-navigator")
    emit(AgentSpawned, agent_id="agent-herald", keel_date=t, ttl=3.0, heading="Announce status", spawner_id="system")
    
    # Phase 3: Tasks
    t += 10.0
    time_real.advance(10.0)
    emit(TaskCreated, task_id="task-refit-001", created=t, ttl=60.0, description="Complete engine refit",
         steps=["Remove old parts", "Install new parts", "Test systems"])
    emit(TaskCreated, task_id="task-survey-001", created=t, ttl=30.0, description="Survey fishing grounds",
         steps=["Deploy sonar", "Log readings"])
    emit(TaskCreated, task_id="task-urgent-001", created=t, ttl=5.0, description="Critical fix",
         steps=["Fix leak"])
    emit(TaskCreated, task_id="task-log-001", created=t, ttl=100.0, description="Log navigation data",
         steps=["Collect data", "Write log"])
    
    # Phase 4: Bearings observed
    t += 15.0
    time_real.advance(15.0)
    emit(BearingObserved, observer="agent-navigator", target="tile-hull-001", angle=45.0, rate=0.5, observed_at=t)
    emit(BearingObserved, observer="agent-navigator", target="tile-engine-001", angle=90.0, rate=0.2, observed_at=t)
    emit(BearingObserved, observer="agent-pilot", target="tile-hull-001", angle=10.0, rate=1.0, observed_at=t)
    emit(BearingObserved, observer="agent-engineer", target="tile-engine-001", angle=0.0, rate=0.0, observed_at=t)
    emit(BearingObserved, observer="agent-engineer", target="tile-hull-001", angle=180.0, rate=0.0, observed_at=t)
    emit(BearingObserved, observer="agent-scout", target="tile-keel-001", angle=270.0, rate=-0.3, observed_at=t)
    
    # Phase 5: Trust assertions
    t += 5.0
    time_real.advance(5.0)
    emit(TrustAsserted, subject="agent-navigator", claim="agent-engineer", confidence=0.95, depth=1, asserted_at=t)
    emit(TrustAsserted, subject="agent-navigator", claim="agent-pilot", confidence=0.80, depth=1, asserted_at=t)
    emit(TrustAsserted, subject="system", claim="agent-navigator", confidence=0.99, depth=0, asserted_at=t)
    emit(TrustAsserted, subject="agent-pilot", claim="agent-navigator", confidence=0.70, depth=2, asserted_at=t)
    emit(TrustAsserted, subject="agent-engineer", claim="system", confidence=1.0, depth=0, asserted_at=t)
    emit(TrustAsserted, subject="system", claim="agent-engineer", confidence=0.90, depth=0, asserted_at=t)
    
    # Phase 6: Progress + heartbeats
    t += 10.0
    time_real.advance(10.0)
    emit(TaskStepCompleted, task_id="task-refit-001", step_index=0, completed_at=t)
    emit(TaskStepCompleted, task_id="task-refit-001", step_index=1, completed_at=t)
    emit(AgentHeartbeat, agent_id="agent-navigator", timestamp=t)
    emit(AgentHeartbeat, agent_id="agent-engineer", timestamp=t)
    emit(AgentHeartbeat, agent_id="agent-pilot", timestamp=t)
    emit(AgentHeartbeat, agent_id="agent-scout", timestamp=t)
    # agent-herald never heartbeats — will be silent from the start
    
    # Phase 7: More progress + trust decay
    t += 15.0
    time_real.advance(15.0)
    emit(TrustDecayed, subject="agent-navigator", claim="agent-engineer", new_confidence=0.85)
    emit(TaskStepCompleted, task_id="task-refit-001", step_index=2, completed_at=t)  # task complete!
    emit(TaskStepCompleted, task_id="task-log-001", step_index=0, completed_at=t)
    
    # Phase 8: Pilot stops heartbeating
    t += 25.0
    time_real.advance(25.0)
    emit(AgentHeartbeat, agent_id="agent-navigator", timestamp=t)
    emit(AgentHeartbeat, agent_id="agent-engineer", timestamp=t)
    # agent-pilot silent from here
    
    # Phase 9: Scout's last heartbeat, then it goes silent too
    emit(AgentHeartbeat, agent_id="agent-scout", timestamp=t)
    
    # Phase 10: Final events
    t += 5.0
    time_real.advance(5.0)
    emit(BearingObserved, observer="agent-navigator", target="tile-engine-001", angle=88.0, rate=0.1, observed_at=t)
    
    # Let scout heartbeat expire — advance past its TTL
    t += 8.0  # scout TTL was 10s, first heartbeat at t=50, second at t=85, now t=93 — 8s since last = within 10s TTL
    time_real.advance(8.0)
    # Actually let's advance more so scout expires
    t += 5.0
    time_real.advance(5.0)
    
    # Final trust decay
    emit(TrustDecayed, subject="agent-pilot", claim="agent-navigator", new_confidence=0.55)
    
    # Phase 11: Advance time past pilot's TTL — pilot goes silent
    t += 20.0  # pilot last heartbeat at t=85, now t=113, 28s ago — past TTL of 75s
    time_real.advance(20.0)
    
    # Navigator and engineer still alive — they keep heartbeating
    emit(AgentHeartbeat, agent_id="agent-navigator", timestamp=t)
    emit(AgentHeartbeat, agent_id="agent-engineer", timestamp=t)
    
    # New tile (late addition, fresh)
    emit(TileCreated, tile_id="tile-radio-001", keel_date=t, ttl=300.0, tile_type="radio", data={"range": "100 nmi"})
    
    # Fresh bearing from the only active observers
    emit(BearingObserved, observer="agent-navigator", target="tile-keel-001", angle=180.0, rate=0.0, observed_at=t)
    emit(BearingObserved, observer="agent-engineer", target="tile-radio-001", angle=45.0, rate=2.0, observed_at=t)
    
    # Final events: complete log task, new trust
    emit(TaskStepCompleted, task_id="task-log-001", step_index=1, completed_at=t)  # task complete!
    emit(TrustAsserted, subject="system", claim="tile-radio-001", confidence=0.50, depth=2, asserted_at=t)
    emit(TrustDecayed, subject="system", claim="agent-pilot", new_confidence=0.10)  # trust in pilot decays
    
    # New agent spawned late — will it survive?
    emit(AgentSpawned, agent_id="agent-relay", keel_date=t, ttl=30.0, heading="Relay communications", spawner_id="system")
    
    # One more heartbeat — navigator's last
    t += 5.0
    time_real.advance(5.0)
    emit(AgentHeartbeat, agent_id="agent-engineer", timestamp=t)  # engineer is the last agent standing
    
    # Create a new task with very short TTL that will expire
    emit(TaskCreated, task_id="task-flash-001", created=t, ttl=2.0, description="Quick reaction task",
         steps=["React"])
    
    # Advance past its TTL
    t += 3.0
    time_real.advance(3.0)
    # (task-flash-001 should now be expired)
    
    # agent-relay heartbeats — stays alive
    emit(AgentHeartbeat, agent_id="agent-relay", timestamp=t)
    
    # Let's check where we are
    total_events = len(store)
    print(f"Total events appended: {total_events}")
    print()
    
    # Now advance time to create some interesting expiry scenarios
    # At this point (t = base + 10 + 10 + 15 + 5 + 10 + 15 + 25 + 5 + 8 + 5 = base + 108)
    print(f"Current time: {time_real.now():.1f}")
    print()
    
    # ── Compute the Field ──
    field = Field(store, now=time_real.now())
    
    # Show the field snapshot
    print(field.describe())
    print()
    
    # ── Detailed breakdown ──
    print("═══ DETAILED STATE ═══")
    print()
    
    # Tiles
    print("── Tiles ──")
    for tile in field.tiles.all_tiles():
        status = "ALIVE" if tile.alive else "EXPIRED"
        elapsed = time_real.now() - tile.keel_date
        remaining = max(0, tile.ttl - elapsed)
        print(f"  [{status}] {tile.tile_id} ({tile.tile_type}) "
              f"created t-{elapsed:.0f}s ago, TTL={tile.ttl:.0f}s, "
              f"remaining={remaining:.0f}s")
    
    print()
    
    # Agents
    print("── Agents ──")
    for agent in field.agents.all_agents():
        status = "ALIVE" if agent.alive else "SILENT"
        latest = agent.last_heartbeat if agent.last_heartbeat is not None else agent.keel_date
        elapsed = time_real.now() - latest
        remaining = max(0, agent.ttl - elapsed)
        print(f"  [{status}] {agent.agent_id} heading='{agent.heading}' "
              f"last_signal t-{elapsed:.0f}s ago, TTL={agent.ttl:.0f}s, "
              f"remaining={remaining:.0f}s")
    
    print()
    
    # Tasks
    print("── Tasks ──")
    for task in field.tasks.all_tasks():
        if task.complete:
            status = "COMPLETE"
        elif task.expired:
            status = "EXPIRED"
        else:
            status = "ACTIVE"
        progress = f"{len(task.completed_steps)}/{len(task.steps)} steps"
        print(f"  [{status}] {task.task_id}: {task.description}")
        print(f"           {progress}, TTL={task.ttl:.0f}s")
    
    print()
    
    # Bearings
    print("── Bearings ──")
    for bearing in field.bearings.all_bearings():
        status = "STALE" if bearing.stale else "FRESH"
        elapsed = time_real.now() - bearing.observed_at
        print(f"  [{status}] {bearing.observer} → {bearing.target} "
              f"at {bearing.angle}° ({bearing.rate}°/s) "
              f"observed t-{elapsed:.0f}s ago")
    
    print()
    
    # Trust
    print("── Trust ──")
    for trust in field.trusts.all_trusts():
        print(f"  {trust.subject} → '{trust.claim}': "
              f"confidence={trust.confidence:.2f}, "
              f"depth={trust.depth}")
    
    print()
    print("═══ KEY INSIGHTS ═══")
    print()
    print("1. Death is the absence of later events.")
    print("   agent-pilot stopped heartbeating at t=85.")
    print("   It is now projected as SILENT — not because a")
    print("   'death' event was stored, but because the field")
    print("   computed that no recent events exist for it.")
    print()
    print("2. TTL is a projection property, not a stored field.")
    print("   agent-scout's TTL is 10s. Its last heartbeat was")
    print("   more than 10s ago — projected as SILENT.")
    print()
    print("3. The event store never forgets.")
    print(f"   {total_events} events stored. Every event is preserved.")
    print("   The field is recomputed each time from first principles.")
    print("   No data is lost. No state is mutated.")
    print()
    print("4. The projection IS the field.")
    print("   Queries don't inspect events — they inspect the field,")
    print("   which is a derived view. The field is ephemeral.")
    print("   The events are eternal.")
    
    # Restore original function
    ke._now = original_now


if __name__ == "__main__":
    main()
