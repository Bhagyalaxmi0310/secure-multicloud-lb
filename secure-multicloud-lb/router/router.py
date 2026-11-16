"""Baseline router: round robin over HEALTHY targets, with health checks and decision logs.
Targets come from config (env var TARGETS), never from code, so Render/Railway can later
be swapped for AWS/Azure/GCP by changing URLs only.

  TARGETS="render=https://a.onrender.com,railway=https://b.up.railway.app"
"""
import asyncio
import itertools
import json
import os
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response

TARGETS = dict(t.split("=", 1) for t in os.environ["TARGETS"].split(","))
PROBE_INTERVAL = float(os.getenv("PROBE_INTERVAL", "5"))   # seconds
FAIL_PROBES, RECOVER_PROBES = 2, 3                         # consecutive probes to flip health
POLICY = "round_robin"
LOG_FILE = os.getenv("DECISION_LOG", "decisions.jsonl")

health = {n: {"up": True, "fail": 0, "ok": RECOVER_PROBES} for n in TARGETS}
rr = itertools.count()


async def probe_loop(client: httpx.AsyncClient):
    while True:
        for name, url in TARGETS.items():
            h = health[name]
            try:
                r = await client.get(f"{url}/health", timeout=15)   # long timeout: free tiers wake slowly
                good = r.status_code == 200
            except Exception:
                good = False
            if good:
                h["ok"] += 1; h["fail"] = 0
                if h["ok"] >= RECOVER_PROBES:
                    h["up"] = True
            else:
                h["fail"] += 1; h["ok"] = 0
                if h["fail"] >= FAIL_PROBES:
                    h["up"] = False
        await asyncio.sleep(PROBE_INTERVAL)


@asynccontextmanager
async def lifespan(app):
    app.state.client = httpx.AsyncClient()
    task = asyncio.create_task(probe_loop(app.state.client))
    yield
    task.cancel()
    await app.state.client.aclose()


app = FastAPI(lifespan=lifespan)


def log_decision(rec):
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(rec) + "\n")


@app.get("/_router/status")
def status():
    return {"policy": POLICY, "health": health}


@app.get("/{path:path}")
async def proxy(path: str, request: Request):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex
    eligible = [n for n in TARGETS if health[n]["up"]]          # (later: security gate goes here)
    if not eligible:
        log_decision({"ts": time.time(), "request_id": rid, "decision": "REJECT_NO_TARGET"})
        return Response("no eligible target", status_code=503)
    chosen = eligible[next(rr) % len(eligible)]
    start = time.perf_counter()
    try:
        r = await app.state.client.get(f"{TARGETS[chosen]}/{path}", params=dict(request.query_params),
                                       headers={"x-request-id": rid}, timeout=30)
        code, body, ctype = r.status_code, r.content, r.headers.get("content-type", "application/json")
    except Exception:
        code, body, ctype = 502, b"upstream error", "text/plain"
    ms = (time.perf_counter() - start) * 1000
    log_decision({"ts": time.time(), "request_id": rid, "policy": POLICY, "chosen": chosen,
                  "eligible": eligible, "status": code, "latency_ms": round(ms, 1)})
    return Response(body, status_code=code, media_type=ctype)
