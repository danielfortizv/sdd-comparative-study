import os
import ipaddress
from datetime import datetime, timezone, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

CERTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "certs")
CERT_PATH = os.path.join(CERTS_DIR, "server.crt")
KEY_PATH = os.path.join(CERTS_DIR, "server.key")


def generate_development_certificates() -> None:
    """Generate local development SSL/TLS certificate and private key for localhost and 127.0.0.1."""
    os.makedirs(CERTS_DIR, exist_ok=True)

    if os.path.exists(CERT_PATH) and os.path.exists(KEY_PATH):
        print(f"Development certificates already exist in {CERTS_DIR}")
        return

    print("Generating 2048-bit RSA private key...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Shift Bank Dev"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("frontend"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    with open(KEY_PATH, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    with open(CERT_PATH, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"Development TLS certificate generated at: {CERT_PATH}")
    print(f"Development TLS private key generated at: {KEY_PATH}")


if __name__ == "__main__":
    generate_development_certificates()
