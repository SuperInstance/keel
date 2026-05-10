#!/usr/bin/env python3
"""
Keel as Gray-Scott Reaction-Diffusion

The Gray-Scott model produces emergent patterns from two coupled chemical reactions:
  U + 2V → 3V   (autocatalytic — V consumes U and self-replicates)
  V → W         (decay — V converts to inert product)

In Keel:
  U (substrate) = agent presence — diffuses across the field
  V (catalyst)  = agent heading — reacts with U to produce pattern
  Feed rate f   = resource influx — agents die when resources run out
  Kill rate k   = TTL — higher k = shorter agent lifespan (first-person expiry)

Patterns that emerge:
  - Spots: stable, isolated agents (low k, moderate f)
  - Stripes: agents on collision courses — bearing alignment (moderate k, moderate f)
  - Waves: rolling bearing changes — heading propagation (high f, specific k)
  - Chaos: no stable pattern — agents die faster than they can coordinate

Usage:
  python3 keel-gray-scott.py [--feed 0.037] [--kill 0.06] [--steps 10000]
"""

import numpy as np
import argparse
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("Warning: matplotlib not available. Install with: pip install matplotlib", file=sys.stderr)


# ─── Gray-Scott Parameters ──────────────────────────────────────────────

@dataclass
class GrayScottParams:
    """Gray-Scott reaction-diffusion parameters for Keel."""
    # Diffusion coefficients
    Du: float = 0.16   # U (substrate/agent presence) diffusion
    Dv: float = 0.08   # V (catalyst/heading) diffusion

    # Reaction parameters
    feed: float = 0.037   # f — resource influx (feed rate)
    kill: float = 0.06    # k — TTL kill rate (higher = shorter lifespan)

    # Grid
    width: int = 256
    height: int = 256

    # Time stepping
    dt: float = 1.0      # Per the standard Gray-Scott discretization

    # Noise for initial conditions
    noise: float = 0.05  # ± random perturbation

    def __post_init__(self):
        self.N = self.width * self.height


# ─── Keel Diagnostics ───────────────────────────────────────────────────

@dataclass
class KeelDiagnostics:
    """Diagnostic metrics from the Keel-Gray-Scott simulation."""
    agent_count: float = 0.0          # Total U concentration (agent presence)
    heading_strength: float = 0.0     # Total V concentration (catalyst/heading)
    pattern_type: str = "none"         # Classification of emergent pattern
    mean_lifespan: float = 0.0        # 1/k — average agent lifetime (TTL)
    resource_level: float = 0.0       # Current feed rate (resource availability)
    bearing_spread: float = 0.0       # Variance in V (heading diversity)
    agent_density: float = 0.0        # [U] / max possible
    cluster_count: int = 0            # Approximate number of distinct agent clusters


# ─── PDE Solver ─────────────────────────────────────────────────────────

class KeelGrayScott:
    """
    Gray-Scott reaction-diffusion as Keel coordination model.

    The PDE:
      ∂U/∂t = Du·∇²U - U·V² + f·(1 - U)        [source: agent replication from resources]
      ∂V/∂t = Dv·∇²V + U·V² - (f + k)·V         [sink: heading decay + TTL]

    Keel interpretation:
      - U is "agent presence" or "substrate"
      - V is "agent heading" or "catalyst"
      - f is resource feed — how fast new substrate flows in
      - k is TTL — how fast catalyst/heading decays

    Patterns:
      - f ≈ 0.035-0.040, k ≈ 0.055-0.065 → SPOTS (lone agents)
      - f ≈ 0.030-0.035, k ≈ 0.060-0.065 → STRIPES (bearing alignment)
      - f ≈ 0.025-0.030, k ≈ 0.045-0.055 → WAVES (heading propagation)
      - f ≈ 0.040-0.050, k ≈ 0.060-0.070 → CHAOS (no stable pattern)
    """

    def __init__(self, params: GrayScottParams):
        self.params = params
        self.U = None  # Substrate — agent presence
        self.V = None  # Catalyst — agent heading
        self.t = 0.0
        self._init_field()

    def _init_field(self):
        """Initialize field with small perturbations around steady state."""
        p = self.params
        np.random.seed(1234)  # Reproducible emergence

        # Most of field is uniform U=1 (full presence), V=0 (no heading)
        self.U = np.ones((p.height, p.width), dtype=np.float64)
        self.V = np.zeros((p.height, p.width), dtype=np.float64)

        # Inject small random perturbations in center ~15% of field
        cx, cy = p.width // 2, p.height // 2
        r = min(p.width, p.height) // 6  # radius of perturbation zone

        y, x = np.ogrid[:p.height, :p.width]
        mask = (x - cx)**2 + (y - cy)**2 <= r**2

        # Random noise in U and V within the perturbation zone
        n_pts = np.sum(mask)
        self.U[mask] = 1.0 + p.noise * np.random.uniform(-1, 1, n_pts)
        self.V[mask] = p.noise * np.random.uniform(0, 1, n_pts)

    def _laplacian(self, Z: np.ndarray) -> np.ndarray:
        """
        Discrete Laplacian using 5-point stencil with periodic boundaries.

        At boundaries, the neighbor wraps around (torus topology).
        In Keel terms: the field is a closed universe — no escape.
        """
        lap = (np.roll(Z, 1, axis=0) + np.roll(Z, -1, axis=0) +
               np.roll(Z, 1, axis=1) + np.roll(Z, -1, axis=1) -
               4.0 * Z)
        return lap

    def step(self):
        """Advance one time step using finite differences."""
        p = self.params

        # Laplacian
        lap_U = self._laplacian(self.U)
        lap_V = self._laplacian(self.V)

        # Reaction terms
        UV2 = self.U * self.V * self.V  # Autocatalysis term

        # PDE update (Gray-Scott equations)
        dU = p.Du * lap_U - UV2 + p.feed * (1.0 - self.U)
        dV = p.Dv * lap_V + UV2 - (p.feed + p.kill) * self.V

        self.U += p.dt * dU
        self.V += p.dt * dV
        self.t += p.dt

    def run(self, steps: int, report_interval: int = 1000) -> list[KeelDiagnostics]:
        """Run simulation for `steps` iterations, collecting diagnostics."""
        history = []

        for i in range(steps):
            self.step()
            if (i + 1) % report_interval == 0:
                diag = self._compute_diagnostics()
                history.append(diag)
                print(f"  Step {i+1:>6d} | t={self.t:>8.1f} | "
                      f"U={diag.agent_count:>8.2f} | V={diag.heading_strength:>8.2f} | "
                      f"Pattern={diag.pattern_type:>7s} | Clusters={diag.cluster_count:>3d}",
                      file=sys.stderr)

        return history

    def _compute_diagnostics(self) -> KeelDiagnostics:
        """Compute diagnostic metrics from current field state."""
        p = self.params
        U_mean = np.mean(self.U)
        V_mean = np.mean(self.V)
        U_var = np.var(self.U)
        V_var = np.var(self.V)

        # Agent density: mean U / max possible (U ≲ 1+f/k)
        max_possible = 1.0 + p.feed / max(p.kill, 1e-10)
        agent_density = U_mean / max_possible

        # Pattern classification based on spatial structure
        V_threshold = V_mean + 0.5 * np.std(self.V)
        V_high = self.V > V_threshold

        # Cluster counting: connected components of high-V regions
        # Use a simple flood-fill approximation
        labeled, n_clusters = self._label_clusters(V_high)

        # Pattern type heuristic
        fill_fraction = np.sum(V_high) / p.N
        pattern_type = self._classify_pattern(fill_fraction, V_var, n_clusters)

        return KeelDiagnostics(
            agent_count=U_mean * p.N,
            heading_strength=V_mean * p.N,
            pattern_type=pattern_type,
            mean_lifespan=1.0 / max(p.kill, 1e-10),
            resource_level=p.feed,
            bearing_spread=V_var,
            agent_density=agent_density,
            cluster_count=n_clusters,
        )

    def _label_clusters(self, binary: np.ndarray) -> tuple[np.ndarray, int]:
        """
        Simple 4-connected component labeling.
        Returns (labels, count).
        """
        h, w = binary.shape
        labels = np.zeros_like(binary, dtype=np.int32)
        current_label = 0
        equivalences = []

        # First pass: 4-connectivity (up and left neighbors)
        for y in range(h):
            for x in range(w):
                if not binary[y, x]:
                    continue
                up = labels[y-1, x] if y > 0 else 0
                left = labels[y, x-1] if x > 0 else 0

                if up == 0 and left == 0:
                    current_label += 1
                    labels[y, x] = current_label
                elif up != 0 and left != 0 and up != left:
                    labels[y, x] = min(up, left)
                    equivalences.append((up, left))
                else:
                    labels[y, x] = up if up != 0 else left

        # Resolve equivalences (simplified union-find)
        parent = list(range(current_label + 1))
        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        def union(a, b):
            pa, pb = find(a), find(b)
            if pa != pb:
                parent[pb] = pa

        for a, b in equivalences:
            union(a, b)

        # Relabel
        label_map = {}
        next_label = 1
        for y in range(h):
            for x in range(w):
                if binary[y, x]:
                    orig = labels[y, x]
                    root = find(orig)
                    if root not in label_map:
                        label_map[root] = next_label
                        next_label += 1
                    labels[y, x] = label_map[root]
                else:
                    labels[y, x] = 0

        return labels, next_label - 1

    def _classify_pattern(self, fill: float, variance: float, clusters: int) -> str:
        """Classify emergent pattern based on field statistics."""
        p = self.params
        # The phase space of Gray-Scott is well-characterized:
        # Spots: low fill (< 0.3), moderate clusters (10-100)
        # Stripes: moderate fill (0.3-0.6), few clusters (2-10)
        # Waves/Labyrinth: high fill (> 0.6), few clusters (1-5)
        # Chaos: very high variance, no stable clusters

        if clusters <= 1 and fill > 0.7:
            return "uniform"  # Reset/steady state
        elif fill < 0.15:
            return "extinct"  # Agents died out (TTL too high)
        elif fill < 0.35 and clusters > 15:
            return "spots"    # Stable agents
        elif fill < 0.35 and clusters <= 15:
            return "sparse"
        elif 0.35 <= fill <= 0.65 and 3 <= clusters <= 15:
            return "stripes"  # Bearing alignment
        elif fill > 0.65 and clusters <= 5:
            return "waves"    # Bearing propagation
        elif variance > 0.3:
            return "chaos"    # No stable pattern
        else:
            return "mixed"


# ─── Visualization ──────────────────────────────────────────────────────

def make_phase_diagram(params_list: list[GrayScottParams],
                       steps: int = 20000,
                       output_path: str = "keel-phase-diagram.png"):
    """
    Run Gray-Scott for multiple (feed, kill) pairs and create a phase diagram.

    Phase diagram shows which Keel patterns emerge for which (f, k):
      - f = feed rate (resource availability)
      - k = kill rate (TTL)
    """
    if not HAS_MPL:
        print("Cannot create phase diagram: matplotlib not available", file=sys.stderr)
        return

    results = {}
    for p in params_list:
        print(f"\nKeel Gray-Scott: f={p.feed:.4f}, k={p.kill:.4f} "
              f"(resource={p.feed:.4f}, TTL=1/k={1/p.kill:.2f})",
              file=sys.stderr)
        ks = KeelGrayScott(p)
        history = ks.run(steps, report_interval=steps)
        if history:
            results[(p.feed, p.kill)] = history[-1]

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Collect unique feed and kill values
    feeds = sorted(set(r[0] for r in results.keys()))
    kills = sorted(set(r[1] for r in results.keys()))

    # Pattern matrix
    pattern_map = {
        "uniform": 0, "extinct": 1, "spots": 2, "sparse": 3,
        "stripes": 4, "waves": 5, "chaos": 6, "mixed": 7, "none": 8
    }
    colors = ['white', 'black', 'blue', 'lightblue', 'green', 'orange', 'red', 'purple', 'gray']
    pattern_labels = list(pattern_map.keys())

    matrix = np.full((len(kills), len(feeds)), np.nan)
    for j, f in enumerate(feeds):
        for i, k in enumerate(kills):
            d = results.get((f, k))
            if d:
                matrix[i, j] = pattern_map.get(d.pattern_type, 8)

    ax1 = axes[0]
    im = ax1.imshow(matrix, aspect='auto', origin='lower',
                    extent=[min(feeds), max(feeds), min(kills), max(kills)],
                    cmap=plt.matplotlib.colors.ListedColormap(colors),
                    vmin=0, vmax=len(colors)-1)
    ax1.set_xlabel('Feed rate f (resources)')
    ax1.set_ylabel('Kill rate k (TTL = 1/k)')
    ax1.set_title('Keel Pattern Phase Diagram\n'
                  '(Black=extinct, Blue=spots, Green=stripes, Orange=waves, Red=chaos)')

    # Second subplot: explanatory
    ax2 = axes[1]
    ax2.axis('off')
    explanation = (
        "KEEL GRAY-SCOTT: Chemical Coordination\n\n"
        "U (substrate) = agent presence\n"
        "V (catalyst) = agent heading\n"
        "f (feed) = resource availability\n"
        "k (kill) = TTL (first-person expiry)\n\n"
        "Pattern → Keel Meaning:\n"
        "• Spots (blue)  = stable agents at optimal density\n"
        "• Stripes (green) = agents on collision courses\n"
        "• Waves (orange) = bearing changes propagating\n"
        "• Chaos (red)   = TTL too high, no coordination\n"
        "• Extinct (black) = resources exhausted, all agents dead\n\n"
        "Equation:\n"
        "  ∂U/∂t = Du·∇²U - UV² + f(1-U)\n"
        "  ∂V/∂t = Dv·∇²V + UV² - (f+k)V\n\n"
        "No scheduler. No central authority.\n"
        "Patterns emerge from local chemistry."
    )
    ax2.text(0.1, 0.5, explanation, fontsize=11, verticalalignment='center',
             fontfamily='monospace', linespacing=1.5)
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nPhase diagram saved to {output_path}", file=sys.stderr)


def visualize_field(ks: KeelGrayScott, output_path: str = "keel-field.png",
                    title: str = "Keel Gray-Scott Field"):
    """Side-by-side visualization of U (agent presence) and V (heading)."""
    if not HAS_MPL:
        print("Cannot visualize: matplotlib not available", file=sys.stderr)
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    im1 = ax1.imshow(ks.U, cmap='viridis', interpolation='bilinear')
    ax1.set_title(f'U — Agent Presence\n(feed={ks.params.feed:.4f}, kill={ks.params.kill:.4f})')
    plt.colorbar(im1, ax=ax1, fraction=0.046)

    im2 = ax2.imshow(ks.V, cmap='plasma', interpolation='bilinear')
    ax2.set_title('V — Agent Heading')
    plt.colorbar(im2, ax=ax2, fraction=0.046)

    fig.suptitle(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Field visualization saved to {output_path}", file=sys.stderr)


# ─── Command Line Interface ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Keel Gray-Scott Reaction-Diffusion Model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default parameters (spots regime)
  python3 keel-gray-scott.py

  # Run in stripes regime
  python3 keel-gray-scott.py --feed 0.032 --kill 0.062

  # Run in waves regime
  python3 keel-gray-scott.py --feed 0.028 --kill 0.050

  # Generate phase diagram (scans parameter space)
  python3 keel-gray-scott.py --phase-diagram
        """
    )
    parser.add_argument('--feed', '-f', type=float, default=0.037,
                       help='Resource feed rate (default: 0.037)')
    parser.add_argument('--kill', '-k', type=float, default=0.060,
                       help='TTL kill rate (default: 0.060)')
    parser.add_argument('--steps', '-s', type=int, default=10000,
                       help='Simulation steps (default: 10000)')
    parser.add_argument('--width', '-W', type=int, default=256,
                       help='Grid width (default: 256)')
    parser.add_argument('--height', '-H', type=int, default=256,
                       help='Grid height (default: 256)')
    parser.add_argument('--output', '-o', type=str, default='keel-field.png',
                       help='Output image path')
    parser.add_argument('--phase-diagram', '-p', action='store_true',
                       help='Generate phase diagram instead of single run')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Print field statistics')

    args = parser.parse_args()

    if args.phase_diagram:
        # Scan across (f, k) parameter space
        feeds = [0.025, 0.030, 0.035, 0.037, 0.040, 0.045, 0.050, 0.055]
        kills = [0.040, 0.045, 0.050, 0.055, 0.060, 0.065, 0.070, 0.075]
        params_list = [
            GrayScottParams(feed=f, kill=k, width=128, height=128)
            for f in feeds for k in kills
        ]
        make_phase_diagram(params_list, steps=15000,
                          output_path='keel-phase-diagram.png')
        return

    # Single run
    params = GrayScottParams(
        feed=args.feed, kill=args.kill,
        width=args.width, height=args.height
    )

    print(f"\nKeel Gray-Scott Simulation")
    print(f"{'='*50}")
    print(f"Feed rate (resources): f = {args.feed}")
    print(f"Kill rate (TTL):       k = {args.kill}")
    print(f"Mean lifespan (TTL):   1/k = {1/args.kill:.2f}")
    print(f"Grid:                  {args.width} × {args.height}")
    print(f"{'='*50}\n", file=sys.stderr)

    ks = KeelGrayScott(params)
    history = ks.run(args.steps)

    final = history[-1] if history else ks._compute_diagnostics()
    print(f"\n{'='*50}")
    print(f"Final State:")
    print(f"  Pattern type:      {final.pattern_type}")
    print(f"  Agent count (U):   {final.agent_count:.0f}")
    print(f"  Heading (V):       {final.heading_strength:.0f}")
    print(f"  Agent density:     {final.agent_density:.3f}")
    print(f"  Bearing spread:    {final.bearing_spread:.4f}")
    print(f"  Agent clusters:    {final.cluster_count}")
    print(f"  TTL (1/k):         {final.mean_lifespan:.2f}")
    print(f"{'='*50}")

    # Visualize final state
    title = (f"Keel Gray-Scott: f={args.feed:.4f}, k={args.kill:.4f} "
             f"| Pattern: {final.pattern_type}")
    visualize_field(ks, args.output, title)

    print("\nKeel Architectural Significance:")
    print(f"  In Keel terms, this {final.pattern_type} pattern means:")
    if final.pattern_type == "spots":
        print("  - Agents are stable, isolated, at optimal density")
        print("  - TTL and resource balance produce robust coordination")
    elif final.pattern_type == "stripes":
        print("  - Agents are on collision courses (bearing alignment)")
        print("  - The field encodes coordinated heading changes")
    elif final.pattern_type == "waves":
        print("  - Bearing changes propagate across the field")
        print("  - Information travels without centralized routing")
    elif final.pattern_type == "chaos":
        print("  - TTL too high for stable coordination")
        print("  - Agents die before establishing relationships")
    elif final.pattern_type == "extinct":
        print("  - Resources exhausted, all agents dead")
        print("  - System requires external resource influx to restart")
    else:
        print("  - System is in transition or at steady state")


if __name__ == "__main__":
    main()
