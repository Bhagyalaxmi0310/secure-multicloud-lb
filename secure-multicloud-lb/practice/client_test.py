"""Practice client: sends requests through the router and summarises the result.
No extra packages needed (standard library only).

Examples:
  python client_test.py --url http://localhost:9000 --n 60
  python client_test.py --url http://localhost:9000 --n 200 --concurrency 10 --path "work?duration_ms=200"
"""
import argparse
import json
import statistics
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor


def one(url):
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            body = json.loads(r.read().decode() or "{}")
            return r.status, body.get("provider", "?"), (time.perf_counter() - start) * 1000
    except urllib.error.HTTPError as e:
        return e.code, "-", (time.perf_counter() - start) * 1000
    except Exception:
        return 0, "-", (time.perf_counter() - start) * 1000


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(len(values) * p / 100))] if values else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:9000")
    ap.add_argument("--path", default="identify")
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--concurrency", type=int, default=1)
    a = ap.parse_args()
    target = f"{a.url.rstrip('/')}/{a.path.lstrip('/')}"

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        results = list(ex.map(one, [target] * a.n))
    total = time.perf_counter() - t0

    ok = [r for r in results if r[0] == 200]
    lat = [r[2] for r in ok]
    print(f"\nTarget: {target}   requests: {a.n}   concurrency: {a.concurrency}")
    print(f"Success: {len(ok)}/{a.n}  ({100 * len(ok) / a.n:.1f}%)   Errors: {a.n - len(ok)}")
    print("Status codes:", dict(Counter(r[0] for r in results)))
    print("Served by:", dict(Counter(r[1] for r in ok)))
    if lat:
        print(f"Latency ms  p50={pct(lat, 50):.0f}  p95={pct(lat, 95):.0f}  p99={pct(lat, 99):.0f}  mean={statistics.mean(lat):.0f}")
    print(f"Throughput: {len(ok) / total:.1f} successful req/s\n")


if __name__ == "__main__":
    main()
