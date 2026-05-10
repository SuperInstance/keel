#!/usr/bin/env python3
"""
demo.py — Five Keel TTL automata running simultaneously.

Each automaton demonstrates one Keel TTL type as a cellular automaton rule.
All five run in parallel, rendered side by side, updating every 0.5s.
"""

import sys
import os
import time

# Add parent directory so keel_gol is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keel_gol import (
    Grid,
    TileTtlRule,
    TaskTtlRule,
    AgentTtlRule,
    BearingTtlRule,
    TrustTtlRule,
    render_grid_lines,
    render_side_by_side,
    print_clear,
    BANNER,
)

# ─── Configuration ──────────────────────────────────────────────────────────
# Each automaton gets its own grid with enough space for its pattern.

TILE_GRID_W, TILE_GRID_H = 8, 6
TASK_GRID_W, TASK_GRID_H = 14, 10
AGENT_GRID_W, AGENT_GRID_H = 10, 8
BEARING_GRID_W, BEARING_GRID_H = 18, 12
TRUST_GRID_W, TRUST_GRID_H = 14, 10


# ─── Setup ──────────────────────────────────────────────────────────────────

# 1. TILETTL — 2×2 block that lives for N generations, then dies
tile_grid = Grid(TILE_GRID_W, TILE_GRID_H)
tile_rule = TileTtlRule(tile_grid, lifetime=30)
tile_rule.seed_block(3, 1)

# 2. TASKTTL — Glider moving southeast, dies at boundary
task_grid = Grid(TASK_GRID_W, TASK_GRID_H)
task_rule = TaskTtlRule(task_grid)
task_rule.seed_glider(1, 1)

# 3. AGENTTTL — Blinker oscillator needs neighbors to sustain
agent_grid = Grid(AGENT_GRID_W, AGENT_GRID_H)
agent_rule = AgentTtlRule(agent_grid)
agent_rule.seed_blinker(4, 3)

# 4. BEARINGTTL — Two gliders on paths to intersect
bearing_grid = Grid(BEARING_GRID_W, BEARING_GRID_H)
bearing_rule = BearingTtlRule(bearing_grid)
bearing_rule.seed_glider_southeast(0, 4)    # cluster 1 going SE
bearing_rule.seed_glider_northwest(15, 8)   # cluster 2 going NW

# 5. TRUSTTTL — Diamond pattern that propagates with decay
trust_grid = Grid(TRUST_GRID_W, TRUST_GRID_H)
trust_rule = TrustTtlRule(trust_grid, initial_size=4)
trust_rule.seed_diamond(7, 5)


# ─── Display helper ────────────────────────────────────────────────────────

def build_frame():
    """Render all 5 automata side-by-side with their current state."""
    # Get lines for each grid
    tile_lines = render_grid_lines(tile_grid, 'tile', "   TileTTL  | BIRTH→LIVE→DIE")
    task_lines = render_grid_lines(task_grid, 'conway', "  TaskTTL  | Move then die")
    agent_lines = render_grid_lines(agent_grid, 'conway', "  AgentTTL | Neighbors = output")
    bearing_lines = render_grid_lines(bearing_grid, 'bearing', " BearingTTL | Two clusters")
    trust_lines = render_grid_lines(trust_grid, 'trust', "  TrustTTL | Propagate & decay")

    # Summary lines
    tile_summary = f"  {tile_rule.summary()}"
    task_summary = f"  {task_rule.summary()}"
    agent_summary = f"  {agent_rule.summary()}"
    bearing_summary = f"  {bearing_rule.summary()}"
    trust_summary = f"  {trust_rule.summary()}"

    # Arrange: row 1 = Tile + Task + Agent, row 2 = Bearing + Trust
    row1 = render_side_by_side([
        (tile_lines, tile_summary),
        (task_lines, task_summary),
        (agent_lines, agent_summary),
    ])

    row2 = render_side_by_side([
        (bearing_lines, bearing_summary),
        (trust_lines, trust_summary),
    ])

    return row1 + "\n" + row2


# ─── Legend ─────────────────────────────────────────────────────────────────

LEGEND = """
  Cell key:
    · = dead     ■ = alive (standard)
    ○ = cluster1  ● = cluster2 (bearing)
    1-5 = trust level (trust)
    Death is the default. 75% die immediately.
    
  Press Ctrl+C to exit.
"""


# ─── Main loop ──────────────────────────────────────────────────────────────

def main():
    print_clear()
    print(BANNER)
    print(LEGEND)

    max_generations = 200

    try:
        for gen in range(1, max_generations + 1):
            frame = build_frame()
            # Clear and redraw
            print_clear()
            print(BANNER)
            print(f"  Generation: {gen}")
            print(frame)
            print(LEGEND)

            # Check if all simulations are complete
            all_done = True
            if tile_rule.alive_count() > 0:
                all_done = False
            if task_rule.is_alive():
                all_done = False
            if agent_rule.alive_count() > 0:
                all_done = False
            if bearing_rule.alive_count() > 0:
                all_done = False
            if trust_rule.is_active():
                all_done = False

            if all_done:
                print("")
                print("  ╔══════════════════════════════════════════════════╗")
                print("  ║  ALL SIMULATIONS COMPLETE                       ║")
                print("  ║  Every cell died. The default state.            ║")
                print("  ╚══════════════════════════════════════════════════╝")
                break

            # Step all rules
            tile_rule.step()
            task_rule.step()
            agent_rule.step()
            bearing_rule.step()
            trust_rule.step()

            time.sleep(0.5)

    except KeyboardInterrupt:
        pass

    print_clear()
    print(BANNER)
    print(f"  Ran for {min(gen, max_generations)} generations.")
    print("")

    # Final stats
    print("  ─── Final Stats ───")
    print(f"  TileTTL:    {tile_rule.summary()}")
    print(f"  TaskTTL:    {task_rule.summary()}")
    print(f"  AgentTTL:   {agent_rule.summary()}")
    print(f"  BearingTTL: {bearing_rule.summary()}")
    print(f"  TrustTTL:   {trust_rule.summary()}")
    print("")
    print("  '75% of cells die by default. Life is active maintenance.'")
    print("  'Local rules produce global coordination.'")
    print("  'There is no scheduler. There is only the field.'")
    print("")


if __name__ == "__main__":
    main()
