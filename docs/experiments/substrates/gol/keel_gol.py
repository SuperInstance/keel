#!/usr/bin/env python3
"""
keel_gol.py — Conway's Game of Life as Keel TTL Coordination Substrate

Each Keel TTL type is implemented as a cellular automaton rule on a 2D grid.
Death is the default. Life is active maintenance. The field is the command.
"""

import math
import time
from copy import deepcopy

# ─── Grid ────────────────────────────────────────────────────────────────────

DEAD = 0
ALIVE = 1


class Grid:
    """Rectangular 2D grid of integer-valued cells. Bounded (no wrap)."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.cells = [[DEAD for _ in range(width)] for _ in range(height)]

    def get(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells[y][x]
        return DEAD

    def set(self, x, y, val):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.cells[y][x] = val

    def neighbors(self, x, y):
        """Count non-zero neighbors (Moore neighborhood, 8 cells)."""
        count = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if self.cells[ny][nx] != DEAD:
                        count += 1
        return count

    def alive_count(self):
        return sum(1 for row in self.cells for c in row if c != DEAD)

    def clear(self):
        for y in range(self.height):
            for x in range(self.width):
                self.cells[y][x] = DEAD

    def all_values(self):
        """Return set of all non-zero values on the grid."""
        vals = set()
        for row in self.cells:
            for c in row:
                if c != DEAD:
                    vals.add(c)
        return vals

    def copy(self):
        g = Grid(self.width, self.height)
        g.cells = [row[:] for row in self.cells]
        return g


# ─── TileTtlRule: BIRTH → LIVE → DIE ────────────────────────────────────────
# Life pattern: Block (2×2 stable square). Each cell has a fixed lifetime.
# Generation counter ticks down. When TTL hits 0, the cell dies.
# A block with lifetime N stays stable for N generations, then disappears.
# "Every tile is temporary."

class TileTtlRule:
    name = "TileTTL"
    description = "BIRTH→LIVE→DIE: cell with N-generation counter, dies at 0"
    life_pattern = "2×2 block (stable, then dies)"

    def __init__(self, grid, lifetime=8):
        self.grid = grid
        self.lifetime = lifetime
        self.ttl = [[0 for _ in range(grid.width)] for _ in range(grid.height)]
        self.generation = 0

    def seed_block(self, x, y):
        """2×2 block — the simplest stable Life pattern."""
        for dy in range(2):
            for dx in range(2):
                self.grid.set(x + dx, y + dy, ALIVE)
                self.ttl[y + dy][x + dx] = self.lifetime

    def step(self):
        self.generation += 1
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                if self.grid.get(x, y) == ALIVE:
                    self.ttl[y][x] -= 1
                    if self.ttl[y][x] <= 0:
                        self.grid.set(x, y, DEAD)
                        self.ttl[y][x] = 0

    def alive_count(self):
        return self.grid.alive_count()

    def summary(self):
        gen = self.generation
        alive = self.alive_count()
        return f"Gen {gen:3d} | alive={alive:2d} | block TTL={self.lifetime}"


# ─── TaskTtlRule: Move then die ──────────────────────────────────────────────
# Life pattern: Glider. Standard Conway B3/S23 rules.
# The glider travels across the grid until it hits a boundary — then ALL cells
# die immediately. The glider has no persistence beyond its path.
# "A task crosses the field, reaches the edge, and is done."

class TaskTtlRule:
    name = "TaskTTL"
    description = "Glider traverses grid via Conway rules, dies at boundary"
    life_pattern = "Glider (moves, dies at edge)"

    def __init__(self, grid):
        self.grid = grid
        self.generation = 0
        self.alive = True
        self.edge_hit = False

    def seed_glider(self, x, y):
        """Standard Conway glider heading southeast."""
        pattern = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
        for dx, dy in pattern:
            self.grid.set(x + dx, y + dy, ALIVE)

    def step(self):
        self.generation += 1
        if not self.alive:
            return

        # Compute next state with standard Conway rules
        new_cells = [[DEAD for _ in range(self.grid.width)] for _ in range(self.grid.height)]
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                n = self.grid.neighbors(x, y)
                alive = self.grid.get(x, y)
                if alive and (n == 2 or n == 3):
                    new_cells[y][x] = ALIVE
                elif not alive and n == 3:
                    new_cells[y][x] = ALIVE

        # Check if any alive cell touches a boundary
        self.edge_hit = False
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                if new_cells[y][x] == ALIVE:
                    if x == 0 or x == self.grid.width - 1 or y == 0 or y == self.grid.height - 1:
                        self.edge_hit = True
                        break
            if self.edge_hit:
                break

        self.grid.cells = new_cells

        if self.edge_hit:
            self.alive = False
            self.grid.clear()

    def alive_count(self):
        return self.grid.alive_count()

    def is_alive(self):
        return self.alive and self.grid.alive_count() > 0

    def summary(self):
        gen = self.generation
        alive = self.alive_count()
        status = "RUNNING" if self.is_alive() else "COMPLETE (edge hit)" if self.edge_hit else "COMPLETE (decayed)"
        return f"Gen {gen:3d} | alive={alive:2d} | {status}"


# ─── AgentTtlRule: Survive through output ───────────────────────────────────
# Life pattern: Blinker oscillator (3 cells in a row → 3 cells stacked).
# Modified survival rule: a cell needs at least 2 neighbors to stay alive.
# With 0 or 1 neighbors the cell is "silent" and dies — even if standard
# Conway would let it survive with 2 neighbors.
# A lone beehive without connections = dead agent.
# "Silence is death. Output is survival."

class AgentTtlRule:
    name = "AgentTTL"
    description = "Stay alive through output: ≥2 neighbors, silence (≤1) = die"
    life_pattern = "Blinker oscillator (needs neighbors to sustain)"

    def __init__(self, grid):
        self.grid = grid
        self.generation = 0

    def seed_block(self, x, y):
        """2×2 block."""
        for dy in range(2):
            for dx in range(2):
                self.grid.set(x + dx, y + dy, ALIVE)

    def seed_blinker(self, x, y):
        """3-cell blinker oscillator — oscillates between horizontal and vertical."""
        for dx in range(3):
            self.grid.set(x + dx, y, ALIVE)

    def step(self):
        self.generation += 1
        new_cells = [[DEAD for _ in range(self.grid.width)] for _ in range(self.grid.height)]
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                n = self.grid.neighbors(x, y)
                alive = self.grid.get(x, y)
                if alive:
                    # Strict survival: need 2 or 3 neighbors (standard Conway)
                    # But if you're alive and have 0-1 neighbors, you're silent → die
                    if n == 2 or n == 3:
                        new_cells[y][x] = ALIVE
                else:
                    if n == 3:
                        new_cells[y][x] = ALIVE
        self.grid.cells = new_cells

    def alive_count(self):
        return self.grid.alive_count()

    def summary(self):
        gen = self.generation
        alive = self.alive_count()
        return f"Gen {gen:3d} | alive={alive:2d} | output-driven survival"


# ─── BearingTtlRule: Two clusters, compute bearing angle ────────────────────
# Life pattern: Two gliders on collision course. Each cluster has a label (1, 2).
# We track each cluster's centroid history and compute the angle between their
# movement vectors at each generation.
# "The field reveals relationships. Bearing is the angle between two paths."

class BearingTtlRule:
    name = "BearingTTL"
    description = "Two clusters compute bearing angle from movement vectors"
    life_pattern = "Two gliders on collision course"

    def __init__(self, grid):
        self.grid = grid
        self.generation = 0
        self.centroid_hist1 = []
        self.centroid_hist2 = []
        self.bearing_angle = 0.0
        self.alive1 = True
        self.alive2 = True
        self.collided = False

    def seed_glider_southeast(self, x, y):
        """Glider heading southeast → assigned cluster 1."""
        pattern = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
        for dx, dy in pattern:
            self.grid.set(x + dx, y + dy, 1)

    def seed_glider_northwest(self, x, y):
        """Glider heading northwest → assigned cluster 2."""
        pattern = [(0, 0), (0, 1), (0, 2), (1, 0), (2, 1)]
        for dx, dy in pattern:
            self.grid.set(x + dx, y + dy, 2)

    def _centroid(self, cluster_id):
        cx, cy, n = 0.0, 0.0, 0
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                if self.grid.get(x, y) == cluster_id:
                    cx += x
                    cy += y
                    n += 1
        return (cx / n, cy / n) if n > 0 else None

    def _angle_between(self, v1, v2):
        if v1 is None or v2 is None:
            return 0.0
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        m1 = math.hypot(v1[0], v1[1])
        m2 = math.hypot(v2[0], v2[1])
        if m1 == 0 or m2 == 0:
            return 0.0
        cos_a = max(-1.0, min(1.0, dot / (m1 * m2)))
        return math.degrees(math.acos(cos_a))

    def step(self):
        self.generation += 1
        new_cells = [[DEAD for _ in range(self.grid.width)] for _ in range(self.grid.height)]

        # Conway rules preserving cluster identity through majority voting
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                cell_val = self.grid.get(x, y)
                n = 0
                votes = {1: 0, 2: 0}
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.grid.width and 0 <= ny < self.grid.height:
                            v = self.grid.cells[ny][nx]
                            if v > 0:
                                n += 1
                                if v in votes:
                                    votes[v] += 1

                if cell_val > 0 and (n == 2 or n == 3):
                    # Survive — pick the majority cluster identity
                    if votes[1] > votes[2]:
                        new_cells[y][x] = 1
                    elif votes[2] > votes[1]:
                        new_cells[y][x] = 2
                    else:
                        new_cells[y][x] = cell_val
                elif cell_val == DEAD and n == 3:
                    # Birth — pick majority cluster
                    if votes[1] > votes[2]:
                        new_cells[y][x] = 1
                    elif votes[2] > votes[1]:
                        new_cells[y][x] = 2
                    else:
                        new_cells[y][x] = 1
                # else: dies

        self.grid.cells = new_cells

        # Centroids
        c1 = self._centroid(1)
        c2 = self._centroid(2)

        if c1 is not None:
            self.centroid_hist1.append(c1)
        if c2 is not None:
            self.centroid_hist2.append(c2)

        self.alive1 = c1 is not None
        self.alive2 = c2 is not None

        # Bearing angle from movement vectors
        if len(self.centroid_hist1) >= 2 and len(self.centroid_hist2) >= 2:
            v1 = (self.centroid_hist1[-1][0] - self.centroid_hist1[-2][0],
                  self.centroid_hist1[-1][1] - self.centroid_hist1[-2][1])
            v2 = (self.centroid_hist2[-1][0] - self.centroid_hist2[-2][0],
                  self.centroid_hist2[-1][1] - self.centroid_hist2[-2][1])
            self.bearing_angle = self._angle_between(v1, v2)

        # Detect collision: a cell with both cluster identities nearby
        if c1 is not None and c2 is not None:
            dist = math.hypot(c1[0] - c2[0], c1[1] - c2[1])
            if dist < 3.0:
                self.collided = True

    def alive_count(self):
        return self.grid.alive_count()

    def summary(self):
        gen = self.generation
        alive = self.alive_count()
        angle = self.bearing_angle
        c1s = "✓" if self.alive1 else "✗"
        c2s = "✓" if self.alive2 else "✗"
        coll = " COLLISION!" if self.collided else ""
        return f"Gen {gen:3d} | alive={alive:2d} | C1={c1s} C2={c2s} | θ={angle:5.1f}°{coll}"


# ─── TrustTtlRule: Propagate with decay ────────────────────────────────────
# Life pattern: Pattern that replicates, each copy is smaller.
# Cell values represent "trust level" (5 = high trust, 1 = low trust).
# The pattern spreads: a cell with trust level T spawns new cells with T-1.
# Each propagation hop reduces trust. Eventually trust decays to 1 and dies.
# "Trust propagates through the network, decaying with each hop."

class TrustTtlRule:
    name = "TrustTTL"
    description = "Pattern replicates with decay: each generation is smaller"
    life_pattern = "Replicator with per-hop decay"

    def __init__(self, grid, initial_size=4):
        self.grid = grid
        self.generation = 0
        self.max_trust = initial_size
        self.active = True

    def seed_diamond(self, cx, cy):
        """Diamond pattern where center has highest trust value, edges lower."""
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                dist = abs(x - cx) + abs(y - cy)
                if dist < self.max_trust:
                    val = self.max_trust - dist
                    if val > 0:
                        self.grid.set(x, y, val)

    def step(self):
        self.generation += 1
        new_cells = [[DEAD for _ in range(self.grid.width)] for _ in range(self.grid.height)]

        for y in range(self.grid.height):
            for x in range(self.grid.width):
                val = self.grid.get(x, y)
                n = self.grid.neighbors(x, y)

                if val > 0:
                    # Alive cell: survive with 2-3 neighbors (Conway), decay value
                    if n == 2 or n == 3:
                        # Decay slowly
                        decay = 1 if self.generation % 3 == 0 else 0
                        new_cells[y][x] = max(1, val - decay)
                    # else: dies from overcrowding or isolation
                else:
                    # Dead cell: birth with decayed trust
                    if n == 3:
                        # Average the neighbor trust values, then decay
                        neighbor_vals = []
                        for dy in (-1, 0, 1):
                            for dx in (-1, 0, 1):
                                if dx == 0 and dy == 0:
                                    continue
                                nx, ny = x + dx, y + dy
                                if 0 <= nx < self.grid.width and 0 <= ny < self.grid.height:
                                    v = self.grid.cells[ny][nx]
                                    if v > 0:
                                        neighbor_vals.append(v)
                        if neighbor_vals:
                            avg_trust = sum(neighbor_vals) / len(neighbor_vals)
                            new_cells[y][x] = max(1, int(avg_trust) - 1)

        self.grid.cells = new_cells

        # Update max trust level
        max_val = 0
        for row in self.grid.cells:
            for v in row:
                if v > max_val:
                    max_val = v
        self.max_trust = max_val

        if self.grid.alive_count() == 0:
            self.active = False

    def alive_count(self):
        return self.grid.alive_count()

    def is_active(self):
        return self.active and self.grid.alive_count() > 0

    def summary(self):
        gen = self.generation
        alive = self.alive_count()
        trusts = self.max_trust
        status = "ACTIVE" if self.is_active() else "DECAYED"
        return f"Gen {gen:3d} | alive={alive:2d} | trust={trusts} | {status}"


# ─── Rendering ──────────────────────────────────────────────────────────────

def cell_to_char(val, rule=None):
    """Render a single cell to a 3-character string."""
    if val == DEAD:
        return " · "
    if rule is None:
        return " ■ "
    if rule in ('tile', 'trust'):
        if val > 1:
            return f"{val:2d} "
        return " ■ "
    if rule == 'bearing':
        if val == 1:
            return " ○ "  # cluster 1
        elif val == 2:
            return " ● "  # cluster 2
        return " ■ "
    return " ■ "


def render_grid_lines(grid, rule='conway', title=""):
    """Render a grid to a list of strings (one per line, including border)."""
    lines = []
    if title:
        lines.append(f"  {title}")
    border = "  +" + "─" * (grid.width * 3) + "┐"
    lines.append(border)
    for y in range(grid.height):
        row = "  │"
        for x in range(grid.width):
            row += cell_to_char(grid.get(x, y), rule)
        row += "│"
        lines.append(row)
    border2 = "  └" + "─" * (grid.width * 3) + "┘"
    lines.append(border2)
    return lines


def render_side_by_side(grid_renderings):
    """Combine multiple grid renderings (list-of-lines) side by side.
    
    grid_renderings: list of (list_of_lines, summary_line) pairs.
    Returns a single string with all grids arranged horizontally.
    """
    if not grid_renderings:
        return ""

    # Pad all renderings to same height
    max_h = max(len(r[0]) for r in grid_renderings)
    padded = []
    summaries = []
    for lines, summary in grid_renderings:
        padded.append(lines + [""] * (max_h - len(lines)))
        summaries.append(summary)

    # Concatenate each row horizontally with spacing
    result_lines = []
    spacer = "   "
    for row_idx in range(max_h):
        line = spacer.join(p[row_idx] for p in padded)
        result_lines.append(line)

    result_lines.append("")  # blank line
    result_lines.append("  " + "  │  ".join(summaries))

    return "\n".join(result_lines)


def run_simulation_grid(grid, rule, title, summary_fn):
    """Render a single grid for side-by-side display."""
    lines = render_grid_lines(grid, rule, title)
    summary = summary_fn()
    return (lines, summary)


# ─── Conway standard (for reference / task rule) ────────────────────────────

def conway_step(grid):
    """Standard Conway B3/S23 step. Mutates grid in place."""
    new = [[DEAD for _ in range(grid.width)] for _ in range(grid.height)]
    for y in range(grid.height):
        for x in range(grid.width):
            n = grid.neighbors(x, y)
            alive = grid.get(x, y)
            if alive and (n == 2 or n == 3):
                new[y][x] = ALIVE
            elif not alive and n == 3:
                new[y][x] = ALIVE
    grid.cells = new


# ─── Helpers ────────────────────────────────────────────────────────────────

def print_clear():
    """Clear terminal and move cursor to top-left."""
    print("\033[2J\033[H", end="", flush=True)


# ─── Banner ─────────────────────────────────────────────────────────────────

BANNER = r"""
  ╔══════════════════════════════════════════════════════════════╗
  ║  Keel TTL Engine — Conway's Game of Life as Coordination    ║
  ║                                                             ║
  ║  75% of cells die by default. Life is active maintenance.   ║
  ║  Local rules → global coordination. No scheduler.           ║
  ║  The field is the only command.                             ║
  ╚══════════════════════════════════════════════════════════════╝
"""
