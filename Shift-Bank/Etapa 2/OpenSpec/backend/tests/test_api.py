import json
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import database
import main
import uvicorn


class ApiSmokeTest(unittest.TestCase):
    def test_http_routes_preserve_stage1_and_expose_stage2(self):
        temporary = tempfile.TemporaryDirectory()
        database.DB_PATH = Path(temporary.name) / "api.sqlite3"
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="error"))
        thread = threading.Thread(target=server.run, daemon=True); thread.start()
        try:
            limit = time.time() + 8
            while not server.started and time.time() < limit: time.sleep(.05)
            self.assertTrue(server.started)
            base = f"http://127.0.0.1:{port}"
            def request(path, method="GET", body=None):
                data = None if body is None else json.dumps(body).encode()
                req = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type":"application/json"})
                try:
                    with urllib.request.urlopen(req, timeout=3) as response: return response.status, json.loads(response.read() or b"null")
                except urllib.error.HTTPError as response: return response.code, json.loads(response.read() or b"{}")
            status, accounts = request("/api/accounts")
            self.assertEqual(200,status); self.assertEqual(2,len(accounts))
            status, limits = request("/api/limits")
            self.assertEqual(200,status); self.assertEqual("5000000.00",limits["per_transfer"])
            status, pending = request("/api/transfers","POST",{"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"1000000"})
            self.assertEqual(202,status); self.assertEqual("PENDING_MFA",pending["status"])
            status, _ = request(f"/api/transfers/{pending['transfer_id']}/confirm","POST",{"code":"123456"})
            self.assertEqual(200,status)
            status, beneficiary = request("/api/beneficiaries","POST",{"name":"N","bank_name":"B","routing_number":"123456789","account_number":"1234"})
            self.assertEqual(201,status)
            status, ach = request("/api/ach-transfers","POST",{"source_account_id":"acc_checking","amount":"100","beneficiary_id":beneficiary["id"]})
            self.assertEqual(202,status); self.assertEqual("pending",ach["status"])
            status, schedule = request("/api/recurring-schedules","POST",{"transfer_type":"internal","source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"100","frequency":"monthly"})
            self.assertEqual(200,status); self.assertEqual("active",schedule["status"])
            status, history = request("/api/history")
            self.assertEqual(200,status); self.assertTrue(any(x["transfer_type"]=="ach" for x in history))
        finally:
            server.should_exit = True; thread.join(timeout=5); temporary.cleanup()


if __name__ == "__main__": unittest.main()
