# Practice guide: Router + Render (Cloud A) + Railway (Cloud B) + laptop (Cloud C)

```
Client (browser / client_test.py / Locust)
      v
Router (your laptop, port 9000)
      |--> Cloud A: Render
      |--> Cloud B: Railway
      '--> Cloud C (optional): app on your laptop, port 8001
```

Windows: use PowerShell for the commands marked [Windows]. Mac/Linux: use the normal terminal.

## Step 1. Run Cloud C on your laptop (terminal 1)
    cd app
    pip install -r requirements.txt
    [Mac/Linux]  PROVIDER=laptop uvicorn main:app --port 8001
    [Windows]    $env:PROVIDER="laptop"; uvicorn main:app --port 8001
Test: open http://localhost:8001/identify  (should show provider laptop).

## Step 2. Deploy Cloud A (Render) and Cloud B (Railway)
Same repo, root directory `app`, variables PROVIDER=render / PROVIDER=railway.
Test each: https://YOUR-URL/identify

## Step 3. Start the router (terminal 2)
    cd router
    pip install -r requirements.txt
    [Mac/Linux]
    TARGETS="render=https://A.onrender.com,railway=https://B.up.railway.app,laptop=http://localhost:8001" uvicorn router:app --port 9000
    [Windows]
    $env:TARGETS="render=https://A.onrender.com,railway=https://B.up.railway.app,laptop=http://localhost:8001"; uvicorn router:app --port 9000
Check: http://localhost:9000/_router/status  (all three should say up: true)
(Free services sleep: wait about a minute after the first call.)

## Step 4. Send traffic (terminal 3)
    cd practice
    python client_test.py --url http://localhost:9000 --n 60
Expected: "Served by" shows render, railway and laptop with about 20 each.

## Practice exercises (do them in order, write down what you see)
1. Baseline: run the command above 3 times. Save the numbers (p50, p95, errors).
2. Heavier work: add `--path "work?duration_ms=300" --concurrency 10`. Which cloud is slowest?
3. Failure: press Ctrl+C in terminal 1 (laptop cloud stops). Wait about 15 seconds, check /_router/status
   (laptop should be down), run client_test.py again. Errors should be near 0 and laptop gets no traffic.
4. Recovery: restart terminal 1. After about 3 good probes the laptop returns.
5. Cloud failure: suspend the Render service in its dashboard, repeat steps 3 and 4.
6. Read the logs: open router/decisions.jsonl. Each line is one routing decision.

## Next upgrades to the router (after practice works)
- Add the security gate: a per-target "trusted" flag and a rule list before the round robin.
- Add the adaptive score using /metrics from each cloud.
- Add Spillover and weighted round robin policies.
