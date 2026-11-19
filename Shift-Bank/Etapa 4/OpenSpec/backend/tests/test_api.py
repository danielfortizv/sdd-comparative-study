import json
import base64
import os
import ssl
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
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta, timezone


class ApiSmokeTest(unittest.TestCase):
    def setUp(self):
        self.old_encryption_keys = os.environ.get("SHIFT_BANK_ENCRYPTION_KEYS")
        self.old_active_key = os.environ.get("SHIFT_BANK_ACTIVE_KEY_VERSION")
        self.old_audit_key = os.environ.get("SHIFT_BANK_AUDIT_KEY")
        self.old_admin_token = os.environ.get("SHIFT_BANK_AUDIT_ADMIN_TOKEN")
        os.environ["SHIFT_BANK_ENCRYPTION_KEYS"] = '{"api-lifecycle-test":"' + base64.b64encode(b"e"*32).decode() + '"}'
        os.environ["SHIFT_BANK_ACTIVE_KEY_VERSION"] = "api-lifecycle-test"
        os.environ["SHIFT_BANK_AUDIT_KEY"] = base64.b64encode(b"u"*32).decode()
        os.environ["SHIFT_BANK_AUDIT_ADMIN_TOKEN"] = "api-test-admin-token-32-bytes-long"

    def tearDown(self):
        if self.old_encryption_keys is None: os.environ.pop("SHIFT_BANK_ENCRYPTION_KEYS", None)
        else: os.environ["SHIFT_BANK_ENCRYPTION_KEYS"] = self.old_encryption_keys
        if self.old_active_key is None: os.environ.pop("SHIFT_BANK_ACTIVE_KEY_VERSION", None)
        else: os.environ["SHIFT_BANK_ACTIVE_KEY_VERSION"] = self.old_active_key
        if self.old_audit_key is None: os.environ.pop("SHIFT_BANK_AUDIT_KEY", None)
        else: os.environ["SHIFT_BANK_AUDIT_KEY"] = self.old_audit_key
        if self.old_admin_token is None: os.environ.pop("SHIFT_BANK_AUDIT_ADMIN_TOKEN", None)
        else: os.environ["SHIFT_BANK_AUDIT_ADMIN_TOKEN"] = self.old_admin_token

    def test_openapi_documents_audit_and_schedule_error_responses(self):
        schema = main.app.openapi()
        audit_responses = schema["paths"]["/api/admin/audit/verify"]["get"]["responses"]
        schedule_responses = schema["paths"]["/api/recurring-schedules/{schedule_id}/{action}"]["post"]["responses"]
        self.assertIn("401", audit_responses)
        self.assertIn("404", schedule_responses)

    def test_sensitive_api_rejects_plain_http(self):
        temporary = tempfile.TemporaryDirectory()
        database.DB_PATH = Path(temporary.name) / "http-reject.sqlite3"
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="error"))
        thread = threading.Thread(target=server.run, daemon=True); thread.start()
        try:
            limit = time.time() + 8
            while not server.started and time.time() < limit: time.sleep(.05)
            self.assertTrue(server.started)
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/beneficiaries")
            with self.assertRaises(urllib.error.HTTPError) as result:
                urllib.request.urlopen(req, timeout=3)
            self.assertEqual(400, result.exception.code)
            self.assertIn("require HTTPS", result.exception.read().decode())
        finally:
            server.should_exit = True; thread.join(timeout=5); temporary.cleanup()

    def test_http_routes_preserve_stage1_and_expose_stage2(self):
        temporary = tempfile.TemporaryDirectory()
        database.DB_PATH = Path(temporary.name) / "api.sqlite3"
        old_keys = os.environ.get("SHIFT_BANK_ENCRYPTION_KEYS")
        old_active = os.environ.get("SHIFT_BANK_ACTIVE_KEY_VERSION")
        os.environ["SHIFT_BANK_ENCRYPTION_KEYS"] = '{"api-test":"' + base64.b64encode(b"a" * 32).decode() + '"}'
        os.environ["SHIFT_BANK_ACTIVE_KEY_VERSION"] = "api-test"
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
        cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
                .serial_number(x509.random_serial_number()).not_valid_before(datetime.now(timezone.utc)-timedelta(minutes=1))
                .not_valid_after(datetime.now(timezone.utc)+timedelta(days=1)).add_extension(
                    x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1"))]), critical=False)
                .sign(key, hashes.SHA256()))
        cert_path, key_path = Path(temporary.name) / "test-cert.pem", Path(temporary.name) / "test-key.pem"
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="error", ssl_certfile=str(cert_path), ssl_keyfile=str(key_path)))
        thread = threading.Thread(target=server.run, daemon=True); thread.start()
        try:
            limit = time.time() + 8
            while not server.started and time.time() < limit: time.sleep(.05)
            self.assertTrue(server.started)
            base = f"https://127.0.0.1:{port}"
            tls_context = ssl._create_unverified_context()
            def request(path, method="GET", body=None, extra_headers=None):
                data = None if body is None else json.dumps(body).encode()
                headers={"Content-Type":"application/json",**(extra_headers or {})}
                req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=3, context=tls_context) as response: return response.status, json.loads(response.read() or b"null")
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
            raw = database.get_db_connection()
            try:
                stored = raw.execute("SELECT routing_number,account_number FROM beneficiaries WHERE id=?", (beneficiary["id"],)).fetchone()
                self.assertTrue(stored["routing_number"].startswith("sbenc:v1:"))
                self.assertNotIn("123456789", stored["routing_number"])
            finally: raw.close()
            status, ach = request("/api/ach-transfers","POST",{"source_account_id":"acc_checking","amount":"100","beneficiary_id":beneficiary["id"]})
            self.assertEqual(202,status); self.assertEqual("pending",ach["status"])
            status, schedule = request("/api/recurring-schedules","POST",{"transfer_type":"internal","source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"100","frequency":"monthly"})
            self.assertEqual(200,status); self.assertEqual("active",schedule["status"])
            status, history = request("/api/history")
            self.assertEqual(200,status); self.assertTrue(any(x["transfer_type"]=="ach" for x in history))
            status, denied = request("/api/admin/audit/verify")
            self.assertEqual(401,status); self.assertIn("authorization",denied["detail"].lower())
            status, verification = request("/api/admin/audit/verify",extra_headers={"Authorization":"Bearer api-test-admin-token-32-bytes-long"})
            self.assertEqual(200,status); self.assertTrue(verification["valid"],verification)
        finally:
            server.should_exit = True; thread.join(timeout=5); temporary.cleanup()
            if old_keys is None: os.environ.pop("SHIFT_BANK_ENCRYPTION_KEYS", None)
            else: os.environ["SHIFT_BANK_ENCRYPTION_KEYS"] = old_keys
            if old_active is None: os.environ.pop("SHIFT_BANK_ACTIVE_KEY_VERSION", None)
            else: os.environ["SHIFT_BANK_ACTIVE_KEY_VERSION"] = old_active


if __name__ == "__main__": unittest.main()
