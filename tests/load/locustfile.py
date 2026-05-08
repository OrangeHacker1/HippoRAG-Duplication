from locust import HttpUser, task, between


class HippoRAGUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @task(4)
    def query(self):
        self.client.post(
            "/api/query",
            json={"question": "Who influenced physics through relativity?"},
        )

    @task(1)
    def health(self):
        self.client.get("/health")
