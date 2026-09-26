
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22983728.svg)](https://doi.org/10.5281/zenodo.22983728)

# MPLS L3VPN Failure Measurement Study

Reproducible measurement of traffic restoration latency in a BGP/MPLS L3VPN under five failure scenarios.

## Contents

- paper.md — the manuscript
- harness/measure_v3.py — Python measurement harness
- configs/ — full IOL router configurations
- data/ — raw per-trial CSV results
- figures/ — plot script and output figures

## Topology

    CE1 - PE1 - P1 - P2 - PE2 - CE2
           \   \ /   \ /
            \   X     X
             \ / \   / \
              P3 --- P4

8 IOL routers under EVE-NG. Provider core: OSPF area 0 + LDP. Edge: MP-BGP VPNv4, VRF CUST-A.

## Scenarios

- A — Link-down, default OSPF timers
- B — Link-down, sub-second OSPF timers
- C — LDP-IGP synchronization
- D — Silent customer-flow blackhole
- E — LDP session failure only

## Results

| Scenario | T2 median (ms) | T2 p95 (ms) | T3 median (ms) | T3 p95 (ms) |
|----------|----------------|-------------|----------------|-------------|
| A        | 562.72 | 611.04 | 5092.04 | 5490.65 |
| B        | 573.41 | 621.26 | 4753.96 | 5663.50 |
| C        | 565.66 | 577.41 | 4766.64 | 5168.48 |
| D        | 565.98 | 578.55 | 4725.34 | 5339.10 |
| E        | 562.71 | 3530.67 | 4975.28 | 7911.74 |

T2 = first successful ICMP reply after failure injection.
T3 = five consecutive successful replies.

## License

Code: MIT. Paper and data: CC BY 4.0.
