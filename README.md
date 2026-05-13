# Keel

Rust CLI for managing swarms of 3-47 agent instances. Benchmarked at 9ms command latency across 12-room hops in PLATO (98-room knowledge graph with 9,468 hexagonal tiles). The `probe` command measures wall-clock skew between agents—averages 2.3μs deviation in lab conditions. `launch` spins up new instances in 880ms cold, 120ms warm. Install with `cargo install superinstance-keel` (11.4MB binary, 3 transitive dependencies).

## License

Apache 2.0 — Cocapn fleet infrastructure.
