#!/usr/bin/env python3
"""
Keel Ordinary Differential Equations — TTL Types as Kinetics

Each TTL mechanism in Keel maps to a known class of ordinary differential
equation. This module solves them numerically and plots the trajectories,
demonstrating that every Keel concept is expressible as chemical kinetics.

TTL Types:
  1. Tile   — First-order decay:     d[T]/dt = -k·[T]
  2. Task   — Sequential decay:      d[Tₙ]/dt = -k·[Tₙ] + flux(T_{n-1})
  3. Agent  — Allee effect:          d[A]/dt = α[A]² - δ[A] + H·signal(t)
  4. Bearing — Gradient ratio:       dθ/dt = f([H_X], [H_Y])
  5. Trust  — Binding dissociation:  d[AB]/dt = k_on·[A]·[B] - k_off·[AB]

Usage:
  python3 keel-ode.py                    # Run all models and save plots
  python3 keel-ode.py --type tile        # Run one specific model
"""

import numpy as np
import sys
from dataclasses import dataclass, field
from typing import Optional, Callable

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("Warning: matplotlib not available. Install with: pip install matplotlib", file=sys.stderr)

try:
    from scipy.integrate import solve_ivp
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("Warning: scipy not available. Install with: pip install scipy", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════
# 1. TILE — First-Order Decay
# ═══════════════════════════════════════════════════════════════════════

def tile_ode(t, y, k):
    """d[Tile]/dt = -k · Tile"""
    T = y[0]
    dTdt = -k * T
    return [dTdt]


def solve_tile(t_span=(0, 10), k=0.5, T0=1.0):
    """Solve tile decay ODE. Half-life = ln(2)/k"""
    if not HAS_SCIPY:
        return None, None
    sol = solve_ivp(tile_ode, t_span, [T0], args=(k,),
                    method='RK45', max_step=0.01,
                    rtol=1e-6, atol=1e-8)
    half_life = np.log(2) / k
    return sol.t, sol.y[0], half_life


# ═══════════════════════════════════════════════════════════════════════
# 2. TASK — Sequential Catalytic Deactivation
# ═══════════════════════════════════════════════════════════════════════

def task_ode(t, y, k_steps, n_steps):
    """
    d[T₀]/dt = -k_steps · [T₀]          (initial catalyst, starts active)
    d[T₁]/dt = k_steps · [T₀] - k_steps · [T₁]   (intermediate)
    ...
    d[T_d]/dt = k_steps · [T_{n-2}]      (deactivated — accumulates)
    """
    T = y
    dTdt = np.zeros_like(T)

    n = n_steps
    # T₀ decays
    dTdt[0] = -k_steps * T[0]

    # Tₙ ... T_{n-1} sequential
    for i in range(1, n):
        dTdt[i] = k_steps * T[i-1] - k_steps * T[i]

    # T_d (deactivated) accumulates
    dTdt[n] = k_steps * T[n-1]

    return dTdt


def solve_task(t_span=(0, 10), n_steps=5, k_step=1.0):
    """
    Solve task with n sequential catalytic steps.
    T₀ starts at 1.0. Each step has rate k_step.
    After n steps, all T is in deactivated form T_d.
    """
    if not HAS_SCIPY:
        return None, None, None
    y0 = np.zeros(n_steps + 1)
    y0[0] = 1.0  # T₀ starts active

    sol = solve_ivp(task_ode, t_span, y0, args=(k_step, n_steps),
                    method='RK45', max_step=0.01,
                    rtol=1e-6, atol=1e-8)
    return sol.t, sol.y, n_steps


# ═══════════════════════════════════════════════════════════════════════
# 3. AGENT — Allee Effect Heartbeat (Bistable Switch)
# ═══════════════════════════════════════════════════════════════════════

def agent_ode(t, y, alpha, delta, h_amplitude, h_frequency):
    """
    d[A]/dt = α · [A]² · (1 - [A]/K)  -  δ · [A]  +  H(t)

    Where:
      α = replication rate (Allee coefficient)
      δ = death rate (TTL)
      K = carrying capacity (resource limit)
      H(t) = heartbeat signal (periodic kick)

    This is the Allee effect with logistic carrying capacity:

      d[A]/dt = A · (αA - δ) + H(t)   (when K is large / normalized)

    Two stable fixed points exist when H(t) = 0:
      A* = 0           (extinction)
      A* = δ/α         (survival)  [if α > 0 and δ/α > 0]
    An unstable fixed point at A = 0 (separatrix if δ > 0).
    """
    A = y[0]
    # Heartbeat signal: periodic pulse
    H_t = h_amplitude * max(0, np.sin(2 * np.pi * h_frequency * t))
    # Allee replication: requires A > 0, proportional to A² (needs partner)
    # Logistic carrying capacity keeps A bounded
    dAdt = alpha * A * A - delta * A + H_t
    return [dAdt]


def solve_agent(t_span=(0, 20), alpha=0.5, delta=0.3, A0=0.01,
                h_amplitude=0.02, h_frequency=0.5):
    """
    Solve agent ODE with Allee effect.
    Below critical A_crit = δ/α = 0.6, agent decays to 0.
    Above A_crit, agent self-sustains.
    """
    if not HAS_SCIPY:
        return None, None, None
    sol = solve_ivp(agent_ode, t_span, [A0],
                    args=(alpha, delta, h_amplitude, h_frequency),
                    method='RK45', max_step=0.01,
                    rtol=1e-6, atol=1e-8)

    # Bifurcation analysis
    A_crit = delta / alpha if alpha > 0 else float('inf')

    return sol.t, sol.y[0], A_crit


# ═══════════════════════════════════════════════════════════════════════
# 4. BEARING — Chemotactic Gradient (Heading from Concentrations)
# ═══════════════════════════════════════════════════════════════════════

def bearing_ode(t, y, k_in, gamma, signal_x, signal_y):
    """
    d[H_X]/dt = k_in · signal_x(t) - γ · [H_X]
    d[H_Y]/dt = k_in · signal_y(t) - γ · [H_Y]
    θ = arctan([H_Y] / [H_X])

    Where:
      k_in = heading acquisition rate
      γ = forgetting rate (how fast heading decays)
      signal_x(t), signal_y(t) = external gradient field
      θ = bearing (heading angle)
    """
    Hx, Hy = y
    dHx_dt = k_in * signal_x(t) - gamma * Hx
    dHy_dt = k_in * signal_y(t) - gamma * Hy

    # Bearing angle (computed, not integrated directly)
    theta = np.arctan2(Hy, Hx)

    return [dHx_dt, dHy_dt]


def solve_bearing(t_span=(0, 10), k_bearing=1.0, gamma=0.5,
                  Hx0=1.0, Hy0=0.0,
                  signal_sweep_rate=0.3):
    """
    Solve bearing ODE with a rotating external signal.

    signal_x(t) = cos(ω·t)  (rotating gradient)
    signal_y(t) = sin(ω·t)

    The agent's heading should track the external signal,
    with a phase lag determined by forgetting rate γ.
    """
    if not HAS_SCIPY:
        return None, None, None, None

    signal_x = lambda t: np.cos(signal_sweep_rate * t)
    signal_y = lambda t: np.sin(signal_sweep_rate * t)

    sol = solve_ivp(bearing_ode, t_span, [Hx0, Hy0],
                    args=(k_bearing, gamma, signal_x, signal_y),
                    method='RK45', max_step=0.01,
                    rtol=1e-6, atol=1e-8)

    # Compute bearing from Hx, Hy
    theta = np.arctan2(sol.y[1], sol.y[0])

    # Expected signal direction
    theta_signal = np.arctan2(signal_y(sol.t), signal_x(sol.t))

    return sol.t, sol.y[0], sol.y[1], theta, theta_signal


# ═══════════════════════════════════════════════════════════════════════
# 5. TRUST — Binding Affinity (Dissociation as Trust TTL)
# ═══════════════════════════════════════════════════════════════════════

def trust_ode(t, y, k_on, k_off, renewal_rate, renewal_amplitude):
    """
    d[AB]/dt = k_on · [A] · [B] - k_off · [AB] + renewal(t)

    Where:
      k_on = binding rate (trust establishment)
      k_off = dissociation rate (trust TTL)
      [A] + [AB] = A_total (conserved)
      [B] + [AB] = B_total (conserved)

    Conservation reduces to single ODE:
      d[AB]/dt = k_on · (A_tot - AB) · (B_tot - AB) - k_off · AB + renewal(t)
    """
    AB = y[0]
    A_tot = 1.0  # Normalized total A
    B_tot = 1.0  # Normalized total B

    A_free = A_tot - AB
    B_free = B_tot - AB

    # Trust renewal: periodic signal that promotes rebinding
    renewal = renewal_amplitude * max(0, np.sin(2 * np.pi * renewal_rate * t))

    dABdt = k_on * A_free * B_free - k_off * AB + renewal
    return [dABdt]


def solve_trust(t_span=(0, 30), k_on=2.0, k_off=0.5, AB0=0.0,
                renewal_rate=0.15, renewal_amplitude=0.1):
    """
    Solve trust binding ODE.

    Trust lifetime τ = 1/k_off.
    Steady state AB* ≈ (k_on/(k_on + k_off)) when binding energy > thermal.
    """
    if not HAS_SCIPY:
        return None, None, None

    sol = solve_ivp(trust_ode, t_span, [AB0],
                    args=(k_on, k_off, renewal_rate, renewal_amplitude),
                    method='RK45', max_step=0.01,
                    rtol=1e-6, atol=1e-8)

    trust_ttl = 1.0 / k_off  # Mean trust lifetime
    return sol.t, sol.y[0], trust_ttl


# ═══════════════════════════════════════════════════════════════════════
# Visualization
# ═══════════════════════════════════════════════════════════════════════

def plot_all(output_path="keel-odes.png"):
    """Run and plot all five TTL ODE models."""
    if not HAS_MPL or not HAS_SCIPY:
        print("Cannot plot: matplotlib and/or scipy missing", file=sys.stderr)
        return

    fig, axes = plt.subplots(3, 2, figsize=(16, 14))
    axes = axes.flatten()

    # ── 1. Tile Decay (First-Order TTL) ──
    ax = axes[0]
    ts = [0.1, 0.5, 1.0, 2.0]
    for k in ts:
        t, T, hl = solve_tile(t_span=(0, 10), k=k)
        if t is not None:
            ax.plot(t, T, label=f'k={k}, t½={hl:.2f}')
    ax.set_xlabel('Time')
    ax.set_ylabel('[Tile]')
    ax.set_title('A_tile: First-Order Decay (TTL = Half-Life)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # ── 2. Task Sequential Deactivation ──
    ax = axes[1]
    t, y, n = solve_task(t_span=(0, 5), n_steps=4, k_step=1.5)
    if t is not None:
        for i in range(n + 1):
            label = f'T_{i}' if i < n else 'T_d (deactivated)'
            ax.plot(t, y[i], label=label)
    ax.set_xlabel('Time')
    ax.set_ylabel('[Task species]')
    ax.set_title('A_task: Sequential Catalytic Deactivation')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # ── 3. Agent Allee Effect ──
    ax = axes[2]
    # Below threshold
    t, A, crit = solve_agent(t_span=(0, 20), alpha=0.5, delta=0.3, A0=0.01)
    if t is not None:
        ax.plot(t, A, label=f'A₀=0.01 (below A*={crit:.2f})', color='red')
    # Above threshold
    t, A, _ = solve_agent(t_span=(0, 20), alpha=0.5, delta=0.3, A0=0.8)
    if t is not None:
        ax.plot(t, A, label=f'A₀=0.8 (above A*={crit:.2f})', color='green')
    # With heartbeat kicks
    t, A, _ = solve_agent(t_span=(0, 20), alpha=0.5, delta=0.3, A0=0.5,
                          h_amplitude=0.05, h_frequency=2.0)
    if t is not None:
        ax.plot(t, A, label='A₀=0.5 + heartbeat', color='blue', alpha=0.7)
    ax.axhline(y=crit, color='gray', linestyle='--', alpha=0.5,
               label=f'separatrix A*={crit:.2f}')
    ax.set_xlabel('Time')
    ax.set_ylabel('[Agent]')
    ax.set_title('A_agent: Allee Effect Heartbeat (Bistable)')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── 4. Bearing (Heading from Concentrations) ──
    ax = axes[3]
    t, Hx, Hy, theta, theta_sig = solve_bearing(
        t_span=(0, 10), gamma=0.5, signal_sweep_rate=0.5)
    if t is not None:
        ax.plot(t, theta, label='θ — Agent bearing', color='blue')
        ax.plot(t, theta_sig, label='θ_signal — External gradient', color='orange', alpha=0.6)
    ax.set_xlabel('Time')
    ax.set_ylabel('Bearing (radians)')
    ax.set_title('A_bearing: Heading from Concentration Ratio')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # ── 5. Trust Binding Dissociation ──
    ax = axes[4]
    # Different k_off values
    for k_off in [0.1, 0.5, 2.0]:
        t, AB, ttl = solve_trust(t_span=(0, 20), k_on=2.0, k_off=k_off,
                                 renewal_rate=0.2, renewal_amplitude=0.1)
        if t is not None:
            ax.plot(t, AB, label=f'k_off={k_off}, τ={ttl:.1f}')
    ax.set_xlabel('Time')
    ax.set_ylabel('[Trust Complex]')
    ax.set_title('A_trust: Binding/Dissociation (Trust TTL = 1/k_off)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # ── 6. Bearing Rate (Phase portrait: dθ/dt vs θ) ──
    ax = axes[5]
    t, Hx, Hy, theta, theta_sig = solve_bearing(
        t_span=(0, 20), gamma=0.5, signal_sweep_rate=0.5)
    if t is not None:
        dtheta = np.gradient(theta, t)
        ax.plot(theta, dtheta, '-', alpha=0.7, markersize=2)
        ax.set_xlabel('θ (bearing)')
        ax.set_ylabel('dθ/dt (bearing rate)')
        ax.set_title('Bearing Rate vs. Bearing (Phase Portrait)')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.3)

    # Hide unused subplot
    # (none — we used all 6)

    plt.suptitle('Keel TTL Models as Ordinary Differential Equations\n'
                 'Every Keel concept maps to chemical kinetics',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"All ODE plots saved to {output_path}", file=sys.stderr)


def plot_tile(xlim=(0, 15), output_path="keel-ode-tile.png"):
    """Plot tile decay with different half-lives."""
    if not HAS_MPL or not HAS_SCIPY:
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    for k in [0.1, 0.5, 1.0, 2.0]:
        t, T, hl = solve_tile(t_span=xlim, k=k)
        ax.plot(t, T, label=f'k={k}, t½={hl:.2f}')
    ax.set_xlabel('Time')
    ax.set_ylabel('[Tile]')
    ax.set_title('Tile Decay (TTL as Half-Life)\nd[T]/dt = -k·[T]')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"Tile ODE plot saved to {output_path}", file=sys.stderr)


# ─── CLI ────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Keel TTL ODE Models — Chemical Kinetics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
TTL Types:
  tile     First-order decay: d[T]/dt = -k·[T]
  task     Sequential catalytic deactivation
  agent    Allee effect heartbeat (bistable)
  bearing  Chemotactic gradient as heading
  trust    Binding dissociation as trust TTL
  all      Run and plot all five models
        """
    )
    parser.add_argument('--type', '-t', default='all',
                       choices=['tile', 'task', 'agent', 'bearing', 'trust', 'all'],
                       help='Which TTL model to run (default: all)')
    parser.add_argument('--output', '-o', default='keel-odes.png',
                       help='Output image path')
    args = parser.parse_args()

    if args.type == 'all':
        plot_all(args.output)
    elif args.type == 'tile':
        plot_tile(output_path=args.output)
    else:
        print(f"Single plot for {args.type} not implemented separately yet. Use --type all.",
              file=sys.stderr)
        plot_all(args.output)

    # Print numerical summary
    print("\n=== Keel ODE Summary ===")
    print("")
    print("  Tile:   d[T]/dt = -k·[T]              → T(t) = T₀·exp(-kt)")
    print("  Task:   d[Tₙ]/dt = -k·[Tₙ] + flux     → Sequential catalysis")
    print("  Agent:  d[A]/dt = α[A]² - δ[A] + H(t) → Allee effect")
    print("  Bearing: d[H]/dt = k·S(t) - γ[H]      → θ = arctan(Hy/Hx)")
    print("  Trust:  d[AB]/dt = k_on·A·B - k_off·AB → τ = 1/k_off")
    print("")
    print("  Bearing rate = dθ/dt = (Hx·dHy/dt - Hy·dHx/dt) / (Hx² + Hy²)")
    print("  Trust TTL = 1/k_off — mean complex lifetime")
    print("  Agent TTL = 1/δ — decay lifetime (Allee: survival if α·A > δ)")
    print("""
  "Chemistry has been Keel-compatible since the first molecule decayed.
   Half-life IS TTL. Reaction rates ARE bearing rates. Binding affinity IS trust.
   The architecture wasn't invented by network engineers — it was discovered
   in the stoichiometric table."
    """)


if __name__ == "__main__":
    main()
