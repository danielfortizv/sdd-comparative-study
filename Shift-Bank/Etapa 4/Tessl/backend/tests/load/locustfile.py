import random
from locust import HttpUser, task, between, events

# Custom counters for fine-grained SLA evaluation
business_rejections_count = 0


@events.reset_stats.add_listener
def on_reset_stats(**kwargs):
    global business_rejections_count
    business_rejections_count = 0


class BankingUser(HttpUser):
    # Think time between 0.5s and 1.5s
    wait_time = between(0.5, 1.5)

    def on_start(self):
        # Alternate transfers between Primary Checking (1) and Standard Savings (2)
        self.toggle_direction = random.choice([True, False])

    @task(60)
    def query_balance(self):
        """60% Weight: Account balance queries."""
        if random.random() < 0.5:
            self.client.get("/api/accounts", name="GET /api/accounts")
        else:
            acc_id = 1 if random.random() < 0.5 else 2
            self.client.get(f"/api/accounts/{acc_id}", name="GET /api/accounts/{id}")

    @task(30)
    def query_transaction_history(self):
        """30% Weight: Transaction history queries."""
        if random.random() < 0.5:
            self.client.get("/api/transactions", name="GET /api/transactions")
        else:
            acc_id = 1 if random.random() < 0.5 else 2
            self.client.get(
                f"/api/transactions?account_id={acc_id}",
                name="GET /api/transactions?account_id={id}",
            )

    @task(10)
    def execute_internal_transfer(self):
        """10% Weight: Internal transfers alternating between accounts."""
        global business_rejections_count
        self.toggle_direction = not self.toggle_direction
        from_id = 1 if self.toggle_direction else 2
        to_id = 2 if self.toggle_direction else 1

        payload = {
            "from_account_id": from_id,
            "to_account_id": to_id,
            "amount": 1.00,
            "description": "Locust load benchmark transfer",
        }

        with self.client.post(
            "/api/transfers",
            json=payload,
            name="POST /api/transfers",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                response.success()
            elif response.status_code == 400 and (
                "limit" in response.text.lower() or "insufficient" in response.text.lower()
            ):
                # Expected business rule enforcement
                business_rejections_count += 1
                response.success()
            else:
                response.failure(f"Unexpected failure {response.status_code}: {response.text}")
