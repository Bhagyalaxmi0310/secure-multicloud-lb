import json
import logging
import os
import time
import uuid

from fastapi import FastAPI, HTTPException, Request

PROVIDER = os.getenv("PROVIDER", "local")   # e.g. render, railway, koyeb, aws
REGION = os.getenv("REGION", "unknown")
VERSION = "1.0.0"
INSTANCE = uuid.uuid4().hex[:8]
MAX_WORK_MS = 2000                          # hard cap so /work cannot exhaust the server

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("app")

app = FastAPI(title="lb-test-app")
state = {"requests": 0, "errors": 0, "inflight": 0, "total_ms": 0.0}


@app.middleware("http")
async def structured_log(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex
    start = time.perf_counter()
    state["inflight"] += 1
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["x-request-id"] = rid
        return response
    finally:
        ms = (time.perf_counter() - start) * 1000
        state["inflight"] -= 1
        state["requests"] += 1
        state["total_ms"] += ms
        if status >= 500:
            state["errors"] += 1
        # never log tokens, headers or request bodies
        log.info(json.dumps({"ts": time.time(), "request_id": rid, "route": request.url.path,
                             "status": status, "duration_ms": round(ms, 1),
                             "provider": PROVIDER}))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/identify")
def identify():
    return {"provider": PROVIDER, "region": REGION, "version": VERSION, "instance": INSTANCE}


@app.get("/work")
def work(duration_ms: int = 100):
    if duration_ms < 0 or duration_ms > MAX_WORK_MS:
        raise HTTPException(status_code=400, detail=f"duration_ms must be 0-{MAX_WORK_MS}")
    end = time.perf_counter() + duration_ms / 1000
    while time.perf_counter() < end:        # burn CPU for a controlled time
        pass
    return {"done": True, "duration_ms": duration_ms, "provider": PROVIDER}


@app.get("/metrics")
def metrics():
    n = max(1, state["requests"])
    return {"provider": PROVIDER, "requests": state["requests"], "errors": state["errors"],
            "inflight": state["inflight"], "avg_latency_ms": round(state["total_ms"] / n, 1)}
