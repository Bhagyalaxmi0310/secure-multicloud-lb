# Practice setup: two "clouds" on free platforms + baseline router

## 1. Test the app locally
    cd app
    pip install -r requirements.txt
    PROVIDER=local uvicorn main:app --port 8000
    curl localhost:8000/health
    curl localhost:8000/identify
    curl "localhost:8000/work?duration_ms=200"
    curl "localhost:8000/work?duration_ms=999999"     # must return 400

## 2. Build the Docker image
    docker build -t lb-test-app ./app
    docker run -p 8000:8000 -e PROVIDER=local lb-test-app

## 3. Deploy the SAME app twice
Push this repo to GitHub, then create one web service per platform pointing at app/Dockerfile.
Set environment variables:
- Service 1 (e.g. Render):  PROVIDER=render   REGION=<region shown>
- Service 2 (e.g. Railway): PROVIDER=railway  REGION=<region shown>
Open  https://<service-url>/identify  on each one to confirm.

## 4. Run the router (on your laptop or Colab)
    cd router
    pip install -r requirements.txt
    TARGETS="render=https://YOUR-A.onrender.com,railway=https://YOUR-B.up.railway.app" \
      uvicorn router:app --port 9000
    curl localhost:9000/identify      # repeat: provider should alternate
    curl localhost:9000/_router/status
Every request is logged in decisions.jsonl (request id, chosen target, status, latency).

## 5. Test the failure behaviour
Suspend one service in its dashboard. After about 2 probe intervals the router marks it down and
stops sending traffic; resume it and it returns after 3 good probes.
(Free tiers sleep when idle: the first request can be slow. That is normal.)

## 6. Moving to AWS / Azure / GCP later
Only the TARGETS URLs and the PROVIDER / REGION variables change. App and router code stay the same.
