#!/usr/bin/env python3
import csv, os, statistics
import matplotlib.pyplot as plt

BASE = os.path.expanduser("~/mpls-l3vpn-measurement/data")
scenarios = ["A", "B", "C", "D", "E"]
labels = ["A\nlink-down\ndefault", "B\nlink-down\nfast-timer",
          "C\nLDP-IGP\nsync", "D\nsilent\nblackhole", "E\nLDP session\nfailure"]

def load(path):
    t2, t3 = [], []
    with open(path) as f:
        for r in csv.DictReader(f):
            if r.get("t2_first_reply_ms"):
                t2.append(float(r["t2_first_reply_ms"]))
            if r.get("t3_stable_ms"):
                t3.append(float(r["t3_stable_ms"]))
    return t2, t3

def med(v): return statistics.median(v) if v else 0
def p95(v):
    if not v: return 0
    v = sorted(v)
    return v[int(0.95 * len(v)) - 1]

t2_med, t2_p95, t3_med, t3_p95 = [], [], [], []
for s in scenarios:
    t2, t3 = load(os.path.join(BASE, f"scenario_{s}.csv"))
    t2_med.append(med(t2))
    t2_p95.append(p95(t2))
    t3_med.append(med(t3))
    t3_p95.append(p95(t3))

x = range(len(scenarios))
w = 0.2
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar([i - 1.5*w for i in x], t2_med, w, label="T2 median")
ax.bar([i - 0.5*w for i in x], t2_p95, w, label="T2 p95")
ax.bar([i + 0.5*w for i in x], t3_med, w, label="T3 median")
ax.bar([i + 1.5*w for i in x], t3_p95, w, label="T3 p95")
ax.set_xticks(list(x))
ax.set_xticklabels(labels)
ax.set_ylabel("Milliseconds")
ax.set_title("Traffic restoration latency by failure scenario")
ax.legend()
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(__file__), "figure1_scenarios.png"), dpi=150)
print("wrote figure1_scenarios.png")
