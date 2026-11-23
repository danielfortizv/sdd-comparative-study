"""Prepare and run H8-10 against uniquely named disposable Docker resources."""
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[1]
suffix = secrets.token_hex(5)
project = f"sb-h810-{suffix}"
http_port, https_port = 18080, 18443
for port in (http_port, https_port):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", port))

work = Path(tempfile.mkdtemp(prefix=f".{project}-", dir=ROOT))
certs = work / "certs"
certs.mkdir()
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
priv = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
pub = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
(certs / "bank_private.pem").write_bytes(priv)
(certs / "bank_public.pem").write_bytes(pub)
subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(datetime.now(timezone.utc)-timedelta(minutes=1))
        .not_valid_after(datetime.now(timezone.utc)+timedelta(days=2))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1"))]), False)
        .sign(key, hashes.SHA256()))
(certs / "localhost_cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
(certs / "localhost_key.pem").write_bytes(priv)
env = work / "docker.env"
admin = secrets.token_urlsafe(32)
env.write_text("\n".join([
    f"BANK_STORAGE_KEY={secrets.token_hex(32)}", f"AUDIT_SIGNING_KEY={secrets.token_urlsafe(32)}",
    f"AUDIT_ADMIN_KEY={admin}", "ENVIRONMENT=production", "ENABLE_TEST_ENDPOINTS=false", "",
]), encoding="utf-8")
nginx = (ROOT / "deployment" / "nginx.conf").read_text(encoding="utf-8").replace(":8443", f":{https_port}")
nginx_file = work / "nginx.conf"
nginx_file.write_text(nginx, encoding="utf-8")
base = ROOT / "deployment" / "docker-compose.yml"
override = work / "compose.override.yml"
volume = f"{project}_data"
network = f"{project}_network"
override.write_text(f'''services:
  backend:
    container_name: {project}_backend
    env_file: [{env.as_posix()}]
    volumes:
      - h810_data:/app/data
      - {certs.as_posix()}:/app/certs:ro
  nginx:
    container_name: {project}_nginx
    ports: !override ["{http_port}:80", "{https_port}:443"]
    volumes:
      - {nginx_file.as_posix()}:/etc/nginx/nginx.conf:ro
      - {certs.as_posix()}:/etc/nginx/certs:ro
volumes:
  h810_data:
    name: {volume}
  shift_bank_smoke_data:
    name: {volume}
  shift_bank_h6_data:
    name: {project}_unused_h6
  shift_bank_data:
    name: {project}_unused
networks:
  shift_bank_network:
    name: {network}
''', encoding="utf-8")

def run(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, text=True, **kwargs)

common = ["docker", "compose", "-p", project, "-f", str(base), "-f", str(override)]
resolved = run(common + ["config", "--format", "json"], capture_output=True).stdout
config = json.loads(resolved)
assert {s["container_name"] for s in config["services"].values()} == {f"{project}_backend", f"{project}_nginx"}
assert {(p["target"], p["published"]) for p in config["services"]["nginx"]["ports"]} == {
    (80, str(http_port)), (443, str(https_port))
}
assert volume == config["volumes"]["h810_data"]["name"]
assert network in config["networks"]["shift_bank_network"]["name"]
(work / "resolved-compose.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
resolved_yaml = run(common + ["config"], capture_output=True).stdout
resolved_file = work / "resolved-compose.yml"
resolved_file.write_text(resolved_yaml, encoding="utf-8")
isolated = ["docker", "compose", "-p", project, "-f", str(resolved_file)]
run(isolated + ["up", "-d", "--build"])
smoke = ROOT / "deployment" / "smoke_test.py"
run([sys.executable, str(smoke), "--http-url", f"http://localhost:{http_port}",
     "--https-url", f"https://localhost:{https_port}", "--cert-path", str(certs / "localhost_cert.pem"),
     "--admin-key", admin, "--compose-file", str(resolved_file), "--compose-project", project])
