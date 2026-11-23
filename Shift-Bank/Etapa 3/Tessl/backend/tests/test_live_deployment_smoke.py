import time
import json
import base64
import os
import subprocess
import urllib.request
import ssl
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE_URL = "https://localhost"
ADMIN_KEY = "local_dev_admin_secret_key_2026"

# Create SSL context that ignores self-signed dev certificate
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def http_request(method: str, path: str, data: dict = None, headers: dict = None):
    url = f"{BASE_URL}{path}"
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)

    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=10) as resp:
            status = resp.status
            content = resp.read().decode("utf-8")
            return status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        return e.code, json.loads(content) if content else {}


def helper_encrypt_field(plaintext: str, pub_pem: str, key_id: str) -> dict:
    public_key = serialization.load_pem_public_key(pub_pem.encode("ascii"))
    session_key = os.urandom(32)
    iv = os.urandom(12)

    aesgcm = AESGCM(session_key)
    ct_and_tag = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    ciphertext = ct_and_tag[:-16]
    tag = ct_and_tag[-16:]

    encrypted_key = public_key.encrypt(
        session_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    return {
        "__encrypted__": True,
        "key_id": key_id,
        "encrypted_key": base64.b64encode(encrypted_key).decode("ascii"),
        "iv": base64.b64encode(iv).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        "tag": base64.b64encode(tag).decode("ascii"),
    }


def run_deployment_smoke_test():
    print("=== LIVE CONTAINER SMOKE TEST VIA HTTPS (NGINX -> FASTAPI) ===")

    # 1. Healthcheck
    st, body = http_request("GET", "/api/health")
    assert st == 200, f"Healthcheck failed: {st}"
    print("[PASS] 1. HTTPS Healthcheck (GET /api/health) -> 200 OK")

    # 2. Account Reads
    st, accounts = http_request("GET", "/api/accounts")
    assert st == 200 and len(accounts) >= 2, f"Account read failed: {st}"
    chk_acc = next(a for a in accounts if a["account_number"] == "CHK-1001")
    sav_acc = next(a for a in accounts if a["account_number"] == "SAV-2001")
    init_chk_bal = chk_acc["balance"]
    print(f"[PASS] 2. Account Reads (GET /api/accounts) -> CHK-1001: ${chk_acc['balance']}, SAV-2001: ${sav_acc['balance']}")

    # 3. Public Key Exchange
    st, crypto_info = http_request("GET", "/api/crypto/public-key")
    assert st == 200 and "public_key" in crypto_info
    print(f"[PASS] 3. Public Key Exchange (GET /api/crypto/public-key) -> Active Key ID: {crypto_info['key_id']}")

    # 4. Beneficiary Creation with Encrypted Fields
    enc_routing = helper_encrypt_field("123456789", crypto_info["public_key"], crypto_info["key_id"])
    enc_account = helper_encrypt_field("9876543210", crypto_info["public_key"], crypto_info["key_id"])

    st, ben = http_request("POST", "/api/beneficiaries", {
        "name": "Live Docker Recipient",
        "routing_number": enc_routing,
        "account_number": enc_account,
        "bank_name": "Docker Secure Bank",
    })
    assert st == 201 and ben["routing_number"] == "123456789"
    ben_id = ben["id"]
    print(f"[PASS] 4. Beneficiary Creation with Client-Side Field Encryption (POST /api/beneficiaries) -> ID {ben_id}")

    # 5. Internal Transfer under threshold ($25.00)
    st, trf = http_request("POST", "/api/transfers", {
        "from_account_id": chk_acc["id"],
        "to_account_id": sav_acc["id"],
        "amount": 25.00,
        "description": "Docker live smoke transfer",
    })
    assert st == 200, f"Transfer failed: {st} {trf}"
    print(f"[PASS] 5. Internal Transfer (POST /api/transfers) -> Transfer ID {trf['id']}")

    # 6. Sensitive Transfer requiring MFA PIN ($1,500.00)
    st, mfa_req = http_request("POST", "/api/transfers", {
        "from_account_id": chk_acc["id"],
        "to_account_id": sav_acc["id"],
        "amount": 1500.00,
    })
    assert st == 428, f"Expected 428 MFA_REQUIRED, got {st}"

    st, mfa_trf = http_request("POST", "/api/transfers", {
        "from_account_id": chk_acc["id"],
        "to_account_id": sav_acc["id"],
        "amount": 1500.00,
        "pin": "1234",
    })
    assert st == 200, f"MFA transfer failed: {st} {mfa_trf}"
    print(f"[PASS] 6. Sensitive Transfer with MFA PIN (POST /api/transfers) -> Transfer ID {mfa_trf['id']}")

    # 7. Audit Chain Verification
    st, audit_res = http_request("GET", "/api/audit/verify", headers={"X-Admin-Key": ADMIN_KEY})
    assert st == 200 and audit_res["valid"] is True
    initial_audit_count = audit_res["total_records"]
    print(f"[PASS] 7. Cryptographic Audit Chain Verification (GET /api/audit/verify) -> Valid: True, Total Records: {initial_audit_count}")

    # 8. Test Data Persistence across Docker Compose restart
    print("\nExecuting 'docker compose restart' to verify data volume persistence...")
    compose_env = os.environ.copy()
    compose_env.setdefault("ENCRYPTION_KEY", "01234567890123456789012345678901")
    compose_env.setdefault("AUDIT_SECRET_KEY", "local_dev_audit_secret_key_32b!")
    compose_env.setdefault("ADMIN_SECRET_KEY", "local_dev_admin_secret_key_2026")
    cmd = ["docker", "compose"]
    test_compose = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docker-compose.test.yml"))
    if os.path.exists(test_compose):
        cmd.extend(["-f", "docker-compose.yml", "-f", "docker-compose.test.yml"])
    cmd.append("restart")
    res = subprocess.run(cmd, env=compose_env, capture_output=True, text=True)
    assert res.returncode == 0, f"Restart failed: {res.stderr}"

    # Wait for service recovery
    time.sleep(6)
    st, _ = http_request("GET", "/api/health")
    for _ in range(10):
        if st == 200:
            break
        time.sleep(2)
        st, _ = http_request("GET", "/api/health")
    assert st == 200, "Server did not recover after restart"
    print("[PASS] 8. Containers successfully restarted and healthy.")

    # 9. Verify Post-Restart Data and Audit Chain
    st, post_bens = http_request("GET", "/api/beneficiaries")
    assert any(b["id"] == ben_id for b in post_bens), "Beneficiary lost after restart!"

    st, post_audit = http_request("GET", "/api/audit/verify", headers={"X-Admin-Key": ADMIN_KEY})
    assert post_audit["valid"] is True and post_audit["total_records"] >= initial_audit_count, "Audit ledger corrupted after restart!"
    print(f"[PASS] 9. Volume Persistence Verified: Beneficiary {ben_id} persisted, Audit Chain valid ({post_audit['total_records']} records).")

    print("\n=== ALL DOCKER COMPOSE DEPLOYMENT SMOKE TESTS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    run_deployment_smoke_test()
