# Keel on the Metal

## The five TTL types, bare-metal C, no OS, no stdlib

The hardware gate design proved the architecture holds in silicon.
This implementation runs that design on real hardware.

### Target: ARM Cortex-M4 (STM32F4)

Why: Cortex-M4 has:
- Hardware timers (TIM) — the TTL counter IS the timer peripheral
- NVIC interrupt controller — death interrupt fires when timer expires
- Memory-mapped GPIO — output IS presence, silence IS death
- No OS, no MMU — bare metal, direct hardware access

### The Architecture

Each TTL type maps to a hardware timer:
- TileTtl = TIM in one-pulse mode: count down from N, stop at 0, fire interrupt, never restart
- TaskTtl = TIM with DMA: each step = one DMA transfer, counter decrements per transfer
- AgentTtl = TIM with output compare: toggle output pin on each period. Stop toggling = death
- BearingTtl = two TIMs with cross-coupled triggers: one stops first = collision interrupt
- TrustTtl = TIM with pulse-width modulation: duty cycle = confidence, decays over time

No scheduler. No OS. The hardware IS the TTL engine.
