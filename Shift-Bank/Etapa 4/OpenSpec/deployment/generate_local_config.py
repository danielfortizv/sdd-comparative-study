"""Create ignored local-only secrets and a loopback development certificate."""
from __future__ import annotations

import base64
import datetime as dt
import ipaddress
import json
import secrets
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


ROOT = Path(__file__).resolve().parent
CERT_DIR = ROOT / "certs"
ENV_FILE = ROOT / ".env.local"


def main() -> None:
    if ENV_FILE.exists():
        raise FileExistsError("deployment/.env.local already exists; refusing to replace local credentials")
    cert_path, key_path = CERT_DIR / "dev-cert.pem", CERT_DIR / "dev-key.pem"
    if cert_path.exists() or key_path.exists():
        raise FileExistsError("Development TLS material already exists; refusing to replace it")
    CERT_DIR.mkdir(parents=True, exist_ok=True)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = dt.datetime.now(dt.timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject).issuer_name(subject).public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=2))
        .not_valid_after(now + dt.timedelta(days=14))
        .add_extension(x509.SubjectAlternativeName([
            x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))
        ]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(private_key, hashes.SHA256())
    )
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                   serialization.NoEncryption()))
    (CERT_DIR / ".gitkeep").touch(exist_ok=True)

    encryption_key = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
    audit_key = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
    admin_token = secrets.token_urlsafe(48)
    values = {
        "SHIFT_BANK_ENCRYPTION_KEYS": json.dumps({"e3-local-v1": encryption_key}, separators=(",", ":")),
        "SHIFT_BANK_ACTIVE_KEY_VERSION": "e3-local-v1",
        "SHIFT_BANK_AUDIT_KEY": audit_key,
        "SHIFT_BANK_AUDIT_ADMIN_TOKEN": admin_token,
        "SHIFT_BANK_DB": "/var/lib/shift-bank/bank.db",
        "TLS_CERT_PATH": "./certs/dev-cert.pem",
        "TLS_KEY_PATH": "./certs/dev-key.pem",
    }
    with ENV_FILE.open("x", encoding="utf-8", newline="\n") as target:
        for name, value in values.items():
            target.write(f"{name}={value}\n")
    print("Generated ignored local secrets and loopback development TLS files; secret values were not printed.")


if __name__ == "__main__":
    main()
