# Optional later: pip install locust ; then run
#   locust -f locustfile.py --host http://localhost:9000
# and open http://localhost:8089
from locust import HttpUser, task, between


class User(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(3)
    def identify(self):
        self.client.get("/identify")

    @task(1)
    def work(self):
        self.client.get("/work?duration_ms=200")
