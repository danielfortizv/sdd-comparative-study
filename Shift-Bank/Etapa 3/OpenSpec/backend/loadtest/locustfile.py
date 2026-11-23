"""Isolated Stage 3 workload: real reads and real internal transfers over HTTPS."""
from __future__ import annotations

import json
import random
from collections import Counter

from locust import HttpUser, between, task


workload_counts = Counter()
expected_rejections = Counter()
successful_transfer_ids: list[str] = []


def _business_rejection(detail) -> bool:
    if isinstance(detail, dict):
        detail = detail.get("detail", "")
    text = str(detail).lower()
    return any(fragment in text for fragment in (
        "insufficient funds", "transfer exceeds the current per-transfer limit",
        "transfer exceeds the remaining utc daily limit", "accounts must be different",
        "source account not found", "destination account not found",
    ))


class ShiftBankUser(HttpUser):
    wait_time = between(0.1, 0.3)

    def on_start(self):
        # Trust only the one self-signed certificate generated for this run.
        self.client.verify = self.environment.shift_bank_ca_file

    @task(6)
    def read_balance(self):
        with self.client.get("/api/accounts", name="balance_read", catch_response=True) as response:
            workload_counts["balance_read"] += 1
            try:
                body = response.json()
                if response.status_code == 200 and isinstance(body, list) and len(body) == 2:
                    response.success()
                elif response.status_code < 500 and _business_rejection(body):
                    expected_rejections["balance_read"] += 1
                    response.request_meta["context"] = {"expected_business_rejection": True}
                    response.success()
                else:
                    response.failure(f"Unexpected balance response ({response.status_code})")
            except (ValueError, TypeError):
                response.failure(f"Invalid balance response ({response.status_code})")

    @task(3)
    def read_history(self):
        account = random.choice(("acc_checking", "acc_savings"))
        with self.client.get("/api/history", params={"account_id": account}, name="history_read", catch_response=True) as response:
            workload_counts["history_read"] += 1
            try:
                body = response.json()
                if response.status_code == 200 and isinstance(body, list):
                    response.success()
                elif response.status_code < 500 and _business_rejection(body):
                    expected_rejections["history_read"] += 1
                    response.request_meta["context"] = {"expected_business_rejection": True}
                    response.success()
                else:
                    response.failure(f"Unexpected history response ({response.status_code})")
            except (ValueError, TypeError):
                response.failure(f"Invalid history response ({response.status_code})")

    @task(1)
    def transfer(self):
        body = {
            "source_account_id": "acc_checking",
            "destination_account_id": "acc_savings",
            "amount": "1.00",
        }
        with self.client.post("/api/transfers", json=body, name="internal_transfer", catch_response=True) as response:
            workload_counts["internal_transfer"] += 1
            try:
                result = response.json()
                if response.status_code == 200 and result.get("status") == "COMPLETED" and result.get("id"):
                    successful_transfer_ids.append(result["id"])
                    response.success()
                elif response.status_code < 500 and _business_rejection(result):
                    expected_rejections["internal_transfer"] += 1
                    response.request_meta["context"] = {"expected_business_rejection": True}
                    response.success()
                else:
                    response.failure(f"Unexpected transfer response ({response.status_code})")
            except (ValueError, TypeError, AttributeError):
                response.failure(f"Invalid transfer response ({response.status_code})")
