# Traffic Restoration and Stabilization Latency in a BGP/MPLS L3VPN Under Five Failure Scenarios

**Ghufran Shakeel**
Independent Researcher — Communication Networks, IP/MPLS, Data-Center Networking
ghufr7an@gmail.com
DOI: 10.5281/zenodo.22983728

## Abstract

We present a reproducible measurement study of traffic restoration behavior in a multi-domain BGP/MPLS L3VPN topology. Five failure conditions are injected on the primary path and two timestamps are recorded per trial: time from failure injection to first successful ICMP reply across the VPN (T2) and time to five consecutive successful replies (T3). Across 20 trials per scenario, median T2 was 562.72 ms (link-down, default timers), 573.41 ms (link-down, fast timers), 565.66 ms (LDP-IGP sync), 565.98 ms (silent blackhole), and 562.71 ms (LDP session failure); p95 T2 was 611.04 ms, 621.26 ms, 577.41 ms, 578.55 ms, and 3530.67 ms respectively. Median T3 ranged from 4725.34 ms to 5092.04 ms, with p95 up to 7911.74 ms in the LDP-failure scenario. A key finding is the heavy-tailed nature of LDP session failure: while the median recovery matches baseline, 15% of trials exceed 2 seconds and one trial exceeded 5 seconds. We argue that this is consistent with LDP reconvergence and BGP next-hop re-resolution dominating the tail, and that routing-table convergence should not be conflated with forwarding-plane restoration.

**Keywords:** BGP/MPLS L3VPN, LDP convergence, OSPF, network resilience, control-plane / data-plane restoration.

## 1. Introduction

Service-provider and data-center networks increasingly combine multiple control and forwarding mechanisms. BGP/MPLS L3VPN remains a fundamental architecture for providing isolated customer connectivity over a provider backbone. In operational networks, architectural capability alone does not determine service continuity: failure detection, control-plane reaction, and forwarding-plane reprogramming each contribute to the period during which customer traffic is disrupted. Operators frequently conflate "the route table has converged" with "traffic is flowing again," yet these events can be separated by hundreds of milliseconds or more.

This work addresses a narrow and measurable question: how does traffic restoration time in a BGP/MPLS L3VPN vary across distinct failure modes? We construct a reproducible multi-domain topology with primary and backup paths, inject five failure conditions, and timestamp the moment traffic is restored at 50 ms polling resolution. The objective is not to rank protocols or reproduce a vendor's convergence implementation, but to establish a transparent and reproducible baseline that can be extended to vendor hardware and to larger topologies.

## 2. Background and Related Work

RFC 4364 specifies BGP/MPLS IP VPN procedures in which provider-edge routers exchange customer VPN routes via MP-BGP while the provider core transports traffic using MPLS labels [1]. The IGP (OSPF, RFC 2328 [2]) provides loopback reachability within the provider domain. LDP (RFC 5036 [3]) distributes label bindings along the IGP shortest path, and LDP-IGP synchronization (RFC 5443 [4]) prevents the IGP from advertising a link as usable until LDP has converged on it.

A failure on the primary path requires: (i) the IGP to detect the failure, (ii) SPF to recompute, (iii) LDP to reconverge and produce a new label binding toward the remote PE, and (iv) the forwarding plane to be reprogrammed with the new label stack. Only after (iv) does VPN traffic flow again.

## 3. Methodology

### 3.1 Topology

Eight IOL routers under EVE-NG. Two customer-edge (CE) routers, two provider-edge (PE) routers, four provider (P) routers forming a redundant ring:

    CE1 - PE1 - P1 - P2 - PE2 - CE2
           \   \ /   \ /
            \   X     X
             \ / \   / \
              P3 --- P4

### 3.2 Addressing

| Node | Loopback0 | Role |
|------|-----------|------|
| PE1  | 1.1.1.1/32 | VRF CUST-A, MP-BGP VPNv4, LDP, OSPF |
| P1   | 2.2.2.2/32 | OSPF, LDP |
| P2   | 3.3.3.3/32 | OSPF, LDP |
| P3   | 4.4.4.4/32 | OSPF, LDP |
| P4   | 5.5.5.5/32 | OSPF, LDP |
| PE2  | 6.6.6.6/32 | VRF CUST-A, MP-BGP VPNv4, LDP, OSPF |
| CE1  | 7.7.7.7/32 | Customer Loopback100 = 100.1.1.1/32 |
| CE2  | 8.8.8.8/32 | Customer Loopback100 = 100.2.2.2/32 |

RD/RT for CUST-A: 65000:100.

### 3.3 Failure Scenarios

| ID | Scenario | Injection |
|----|----------|-----------|
| A | Link-down, default OSPF timers | shutdown PE1 E0/2 |
| B | Link-down, sub-second OSPF timers | hello 1s, dead 4s on E0/2, then shutdown |
| C | LDP-IGP synchronization | mpls ldp igp sync on E0/2, then shutdown |
| D | Silent customer-flow blackhole | outbound ACL on E0/2 dropping the flow, link up |
| E | LDP session failure only | clear mpls ldp neighbor * on PE1, IGP up |

### 3.4 Measurement Method

A Python harness connects to PE1 via SSH, injects each failure, and polls "ping vrf CUST-A 100.2.2.2 source 10.100.1.1 repeat 2 timeout 1" every 50 ms until success. Timestamps recorded relative to failure injection:

- T0 - failure injection
- T2 - first successful ICMP reply
- T3 - five consecutive successful replies

Twenty trials per scenario. Between trials the harness restores the failure and waits for steady state.


## 4. Results

| Scenario | T2 median | T2 p95 | T3 median | T3 p95 |
|----------|-----------|--------|-----------|--------|
| A - link-down, default timers | 562.72 | 611.04 | 5092.04 | 5490.65 |
| B - link-down, fast timers    | 573.41 | 621.26 | 4753.96 | 5663.50 |
| C - LDP-IGP sync              | 565.66 | 577.41 | 4766.64 | 5168.48 |
| D - silent blackhole          | 565.98 | 578.55 | 4725.34 | 5339.10 |
| E - LDP session failure       | 562.71 | 3530.67 | 4975.28 | 7911.74 |

## 5. Discussion

### 5.1 Timer tuning does not dominate link-down restoration

Scenarios A and B differ only in OSPF hello/dead interval configuration. Medians differ by 10.69 ms, within run-to-run variance. On the emulated platform, administratively shutting an interface tears down the OSPF adjacency immediately, bypassing the dead timer. Sub-second timers do not accelerate recovery because the dead timer was not the bottleneck.

### 5.2 LDP-IGP synchronization does not change post-failure restoration

Scenario C enables mpls ldp igp sync on the primary link. Median T2 is statistically indistinguishable from A and B. LDP-IGP sync affects advertisement of the link before it becomes usable, not post-failure recovery.

### 5.3 Silent blackholing did not produce the expected slow recovery

Scenario D was intended to model a failure in which the link stays up but customer traffic is dropped. The outbound ACL applied to E0/2 did not trigger IGP reconvergence during the measured window, and the harness observed recovery at the same latency as scenarios A-C. This is a limitation of the injection method: the ACL filtered the customer flow but did not stop the OSPF hellos, so no alternate path was selected during the measured window. We report scenario D as measured but flag it as not exercising the intended failure mode.

### 5.4 LDP session failure produces the heavy tail

Scenario E produces the most interesting result. Median T2 (562.71 ms) matches baseline, indicating that the majority of failures are handled by the same IGP-triggered reconvergence mechanism. But p95 (3530.67 ms) and the maximum exceeding 5 s reveal that in roughly 15% of trials, LDP session reconvergence and BGP next-hop re-resolution dominate the recovery time. During those trials, the IGP route to PE2's loopback (6.6.6.6) remains valid, but the LSP carrying VPN traffic is broken until LDP re-establishes and a new label binding is installed. This asymmetry - routing table valid, forwarding plane broken - is operationally significant.

### 5.5 Stabilization tail

Median T3 ranges from 4.73 s to 5.09 s across scenarios, considerably longer than T2. We interpret T3 minus T2 as the time required for the network to reach a state in which five consecutive 100-byte ICMP packets traverse the VPN without loss.

## 6. Limitations

- Emulated platform (IOL under EVE-NG); absolute values differ on vendor hardware.
- Single topology; scaling behavior not tested.
- Scenario D did not exercise the intended silent-failure mode.
- ICMP traffic only; TCP/UDP restoration may differ.
- No vendor comparison.

## 7. Reproducibility

All artifacts are released: topology, full router configurations, Python harness, raw per-trial CSVs, and figure-generation script.

## 8. Conclusion

We measured traffic restoration latency in a BGP/MPLS L3VPN under five failure scenarios. Link-down, fast timers, LDP-IGP sync, and filtered-flow scenarios restore traffic within a 15 ms band around 560 ms. LDP session failure produces a heavy-tailed distribution in which 15% of trials exceed 2 seconds and one trial exceeded 5 seconds, demonstrating that label-plane failure recovery can lag IGP convergence by an order of magnitude. We argue that routing-table convergence should not be treated as equivalent to forwarding-plane restoration, and that future work should investigate this asymmetry on vendor hardware and at scale.

## References

[1] E. Rosen, Y. Rekhter, "BGP/MPLS IP Virtual Private Networks (VPNs)," RFC 4364, IETF, 2006.
[2] J. Moy, "OSPF Version 2," RFC 2328, IETF, 1998.
[3] L. Andersson, I. Minei, B. Thomas, "LDP Specification," RFC 5036, IETF, 2007.
[4] M. Lasserre, V. Kompella, "LDP IGP Synchronization," RFC 5443, IETF, 2009.
[5] D. Katz, D. Ward, "Bidirectional Forwarding Detection (BFD)," RFC 5880, IETF, 2010.
[6] Y. Rekhter, T. Li, S. Hares, "A Border Gateway Protocol 4 (BGP-4)," RFC 4271, IETF, 2006.

## Publication Status

This is an independent research preprint / technical report. Not peer-reviewed unless an external venue confirms acceptance. Results are generated by the accompanying open-source harness and are not vendor benchmarks.
