#!/usr/bin/env python3
import csv, subprocess, time, statistics, os
from datetime import datetime

PE1_IP   = "1.1.1.1"
SSH_USER = "admin"
SSH_PASS = "cisco"
TARGET   = "100.2.2.2"
SOURCE   = "10.100.1.1"
TRIALS   = 20
POLL     = 0.05

SCENARIO = os.environ.get("SCENARIO", "A")
OUT      = f"trials_{SCENARIO}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

SSH_OPTS = [
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "ConnectTimeout=3",
    "-o", "LogLevel=ERROR",
    "-o", "KexAlgorithms=+diffie-hellman-group1-sha1",
    "-o", "HostKeyAlgorithms=+ssh-rsa",
    "-o", "PubkeyAcceptedKeyTypes=+ssh-rsa",
    "-o", "Ciphers=+aes128-cbc",
    "-o", "MACs=+hmac-sha1",
]

def ssh(host, cmd, timeout=6):
    try:
        r = subprocess.run(
            ["sshpass", "-p", SSH_PASS, "ssh"] + SSH_OPTS + [f"{SSH_USER}@{host}", cmd],
            capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except subprocess.TimeoutExpired:
        return ""

def ping_once():
    out = ssh(PE1_IP, f"ping vrf CUST-A {TARGET} source {SOURCE} repeat 2 timeout 1")
    return "Success rate is 100" in out

def route_changed():
    out = ssh(PE1_IP, "show ip route 6.6.6.6")
    return "10.0.2.2" in out or "10.0.4" in out

def prep_A():
    ssh(PE1_IP, "configure terminal\ninterface Ethernet0/2\nno shutdown\nno ip ospf hello-interval\nno ip ospf dead-interval\nno ip access-group BLACKHOLE_TEST out\nend")
    time.sleep(3)

def prep_B():
    ssh(PE1_IP, "configure terminal\ninterface Ethernet0/2\nno shutdown\nip ospf hello-interval 1\nip ospf dead-interval 4\nend")
    time.sleep(3)

def prep_C():
    ssh(PE1_IP, "configure terminal\ninterface Ethernet0/2\nno shutdown\nno ip ospf hello-interval\nno ip ospf dead-interval\nmpls ldp igp sync\nend")
    time.sleep(3)

def prep_D():
    ssh(PE1_IP, "configure terminal\nip access-list extended BLACKHOLE_TEST\n deny icmp host 10.100.1.1 host 100.2.2.2\n permit ip any any\ninterface Ethernet0/2\nno shutdown\nno ip ospf hello-interval\nno ip ospf dead-interval\nip access-group BLACKHOLE_TEST out\nend")
    time.sleep(3)

def prep_E():
    ssh(PE1_IP, "configure terminal\ninterface Ethernet0/2\nno shutdown\nno ip ospf hello-interval\nno ip ospf dead-interval\nno ip access-group BLACKHOLE_TEST out\nend")
    time.sleep(2)
    ssh(PE1_IP, "clear mpls ldp neighbor *")
    time.sleep(5)

PREP = {"A": prep_A, "B": prep_B, "C": prep_C, "D": prep_D, "E": prep_E}

def fail_link():
    ssh(PE1_IP, "configure terminal\ninterface Ethernet0/2\nshutdown\nend")

def fail_blackhole():
    ssh(PE1_IP, "configure terminal\ninterface Ethernet0/2\nip access-group BLACKHOLE_TEST out\nend")

def fail_ldp():
    ssh(PE1_IP, "clear mpls ldp neighbor *")

FAIL = {"A": fail_link, "B": fail_link, "C": fail_link, "D": fail_blackhole, "E": fail_ldp}

def recover_link():
    ssh(PE1_IP, "configure terminal\ninterface Ethernet0/2\nno shutdown\nend")

def recover_blackhole():
    ssh(PE1_IP, "configure terminal\ninterface Ethernet0/2\nno ip access-group BLACKHOLE_TEST out\nend")

def recover_ldp():
    time.sleep(5)

RECOVER = {"A": recover_link, "B": recover_link, "C": recover_link,
           "D": recover_blackhole, "E": recover_ldp}

def wait_steady(timeout=60):
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout:
        if ping_once():
            return True
        time.sleep(0.5)
    return False

def one_trial(i):
    PREP[SCENARIO]()
    if not wait_steady(60):
        print(f"[trial {i}] not steady", flush=True)
        return None

    time.sleep(2)
    t0 = time.perf_counter()
    FAIL[SCENARIO]()

    t1 = None
    t2 = None
    t3 = None
    consec = 0
    deadline = t0 + 90
    while time.perf_counter() < deadline:
        now = time.perf_counter()
        if t1 is None and route_changed():
            t1 = now
        if ping_once():
            if t2 is None:
                t2 = now
            consec += 1
            if consec >= 5 and t3 is None:
                t3 = now
                break
        else:
            consec = 0
        time.sleep(POLL)

    RECOVER[SCENARIO]()
    time.sleep(5)

    def ms(t):
        return round((t - t0) * 1000, 2) if t else None

    return {
        "trial": i,
        "t0_utc": datetime.utcnow().isoformat(),
        "scenario": SCENARIO,
        "t1_route_changed_ms": ms(t1),
        "t2_first_reply_ms":   ms(t2),
        "t3_stable_ms":        ms(t3),
        "asymmetry_t2_minus_t1_ms": (round(ms(t2) - ms(t1), 2)
                                     if (t1 and t2) else None),
    }

def main():
    print(f"Running scenario {SCENARIO}, {TRIALS} trials", flush=True)
    rows = []
    for i in range(TRIALS):
        r = one_trial(i)
        if r:
            rows.append(r)
            print(r, flush=True)
        time.sleep(3)

    if not rows:
        print("No successful trials.")
        return

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    for key in ("t1_route_changed_ms", "t2_first_reply_ms",
                "t3_stable_ms", "asymmetry_t2_minus_t1_ms"):
        vals = [r[key] for r in rows if r.get(key) is not None]
        if vals:
            v = sorted(vals)
            n = len(v)
            print(f"{key}: n={n} median={statistics.median(v):.1f} "
                  f"p95={v[int(0.95*n)-1]:.1f} min={min(v):.1f} max={max(v):.1f}")

if __name__ == "__main__":
    main()
