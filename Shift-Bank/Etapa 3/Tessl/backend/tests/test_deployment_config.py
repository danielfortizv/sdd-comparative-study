import os
import sys
import pytest


WORKSPACE_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def test_docker_compose_configuration_file():
    """Asserts that docker-compose.yml defines required services, volumes, and healthchecks without default secrets."""
    compose_path = os.path.join(WORKSPACE_ROOT, "docker-compose.yml")
    assert os.path.exists(compose_path), "docker-compose.yml must exist at project root"

    with open(compose_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Required services
    assert "backend:" in content
    assert "frontend:" in content

    # Backend configuration
    assert "shiftbank_data:/app/data" in content
    assert "DATABASE_URL=sqlite:////app/data/shift_bank.db" in content
    assert "RUN_SCHEDULER=true" in content
    assert "ENCRYPTION_KEY=" in content
    assert "AUDIT_SECRET_KEY=" in content
    assert "ADMIN_SECRET_KEY=" in content

    # No hardcoded known secrets in docker-compose.yml
    assert "01234567890123456789012345678901" not in content, "docker-compose.yml must not contain default encryption secret"
    assert "local_dev_audit_secret_key" not in content, "docker-compose.yml must not contain default audit secret"
    assert "local_dev_admin_secret_key" not in content, "docker-compose.yml must not contain default admin secret"

    # Healthcheck
    assert "healthcheck:" in content
    assert "http://localhost:8000/api/health" in content

    # Frontend / Nginx configuration (ports mapped to unprivileged container ports)
    assert ("80:80" in content or "80:8080" in content)
    assert ("443:443" in content or "443:8443" in content)
    assert "service_healthy" in content
    assert "shiftbank_data:" in content


def test_dockerfiles_structure():
    """Asserts that backend and frontend Dockerfiles exist, use non-root users, and meet specifications."""
    backend_dockerfile = os.path.join(WORKSPACE_ROOT, "backend", "Dockerfile")
    frontend_dockerfile = os.path.join(WORKSPACE_ROOT, "frontend", "Dockerfile")

    assert os.path.exists(backend_dockerfile)
    assert os.path.exists(frontend_dockerfile)

    with open(backend_dockerfile, "r", encoding="utf-8") as f:
        backend_content = f.read()
    assert "python:3.13-slim" in backend_content
    assert "HEALTHCHECK" in backend_content
    assert "uvicorn" in backend_content
    assert "USER appuser" in backend_content

    with open(frontend_dockerfile, "r", encoding="utf-8") as f:
        frontend_content = f.read()
    assert "AS builder" in frontend_content
    assert "nginx:alpine" in frontend_content
    assert "npm run build" in frontend_content
    assert "USER nginx" in frontend_content


def test_nginx_configuration_rules():
    """Asserts that nginx.conf specifies HTTP to HTTPS redirect, TLS termination, and API routing."""
    nginx_conf = os.path.join(WORKSPACE_ROOT, "nginx", "nginx.conf")
    assert os.path.exists(nginx_conf)

    with open(nginx_conf, "r", encoding="utf-8") as f:
        content = f.read()

    # Port redirect
    assert ("listen 80;" in content or "listen 8080;" in content)
    assert "return 301 https://$host$request_uri;" in content

    # SSL termination
    assert ("listen 443 ssl;" in content or "listen 8443 ssl;" in content)
    assert "ssl_certificate /etc/nginx/certs/server.crt;" in content
    assert "ssl_certificate_key /etc/nginx/certs/server.key;" in content
    assert "TLSv1.2 TLSv1.3;" in content

    # Reverse proxy routing
    assert "location /api/ {" in content
    assert "proxy_pass http://backend:8000;" in content
    assert "location / {" in content
    assert "try_files $uri $uri/ /index.html;" in content


def test_env_example_documentation():
    """Asserts that .env.example documents all required secrets and configuration keys without default secrets."""
    env_example = os.path.join(WORKSPACE_ROOT, ".env.example")
    assert os.path.exists(env_example)

    with open(env_example, "r", encoding="utf-8") as f:
        content = f.read()

    assert "ENCRYPTION_KEY=" in content
    assert "AUDIT_SECRET_KEY=" in content
    assert "ADMIN_SECRET_KEY=" in content
    assert "DATABASE_URL=" in content

    # Defaults removed from .env.example
    assert "01234567890123456789012345678901" not in content


def test_development_tls_certificates_validity(monkeypatch):
    """Asserts that generated TLS certificate in nginx/certs is reproducible from clean checkout and has localhost SAN."""
    cert_path = os.path.join(WORKSPACE_ROOT, "nginx", "certs", "server.crt")
    key_path = os.path.join(WORKSPACE_ROOT, "nginx", "certs", "server.key")

    # If certificates are absent (e.g. fresh clone), automatically invoke generator to verify reproducibility
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        if WORKSPACE_ROOT not in sys.path:
            monkeypatch.syspath_prepend(WORKSPACE_ROOT)
        from nginx.generate_certs import generate_development_certificates
        generate_development_certificates()

    assert os.path.exists(cert_path)
    assert os.path.exists(key_path)

    from cryptography import x509
    with open(cert_path, "rb") as f:
        cert = x509.load_pem_x509_certificate(f.read())

    # Check subject and SAN extension
    san_ext = cert.extensions.get_extension_for_oid(x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
    names = [name.value for name in san_ext.value]
    assert "localhost" in names


def test_validate_admin_key_at_startup_enforcement(monkeypatch):
    """Asserts that validate_admin_key_at_startup enforces ADMIN_SECRET_KEY presence in non-testing mode."""
    from backend.app.main import validate_admin_key_at_startup

    # When testing mode is false and ADMIN_SECRET_KEY is absent, must fail fast
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.delenv("ADMIN_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ADMIN_SECRET_KEY environment variable is missing or empty"):
        validate_admin_key_at_startup()

    # When ADMIN_SECRET_KEY is provided, must succeed
    monkeypatch.setenv("ADMIN_SECRET_KEY", "strong_admin_secret_key_2026")
    validate_admin_key_at_startup()

    # When TESTING is true, missing key does not abort test processes
    monkeypatch.delenv("ADMIN_SECRET_KEY", raising=False)
    monkeypatch.setenv("TESTING", "true")
    validate_admin_key_at_startup()


def test_validate_encryption_key_at_startup_enforcement(monkeypatch):
    """Asserts that validate_encryption_key_at_startup enforces ENCRYPTION_KEY presence and length in non-testing mode."""
    from backend.app.services.crypto_service import validate_encryption_key_at_startup

    monkeypatch.setenv("TESTING", "false")
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Cryptographic initialization failure"):
        validate_encryption_key_at_startup()

    # Invalid key length
    monkeypatch.setenv("ENCRYPTION_KEY", "too_short")
    with pytest.raises(RuntimeError, match="Cryptographic initialization failure"):
        validate_encryption_key_at_startup()

    # Valid 32-byte key
    monkeypatch.setenv("ENCRYPTION_KEY", "01234567890123456789012345678901")
    validate_encryption_key_at_startup()


def test_validate_audit_key_at_startup_enforcement(monkeypatch):
    """Asserts that validate_audit_key_at_startup enforces AUDIT_SECRET_KEY presence and length in non-testing mode."""
    from backend.app.services.audit_service import validate_audit_key_at_startup

    monkeypatch.setenv("TESTING", "false")
    monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="AUDIT_SECRET_KEY environment variable is missing or empty"):
        validate_audit_key_at_startup()

    # Key too short (< 16 bytes)
    monkeypatch.setenv("AUDIT_SECRET_KEY", "short_key")
    with pytest.raises(RuntimeError, match="AUDIT_SECRET_KEY must be at least 16 bytes"):
        validate_audit_key_at_startup()

    # Valid key (>= 16 bytes)
    monkeypatch.setenv("AUDIT_SECRET_KEY", "valid_audit_signing_key_32b!")
    validate_audit_key_at_startup()


def test_generate_development_certificates_fresh_and_idempotent(tmp_path, monkeypatch):
    """Asserts that generate_development_certificates creates valid X.509 certs and runs idempotently."""
    if WORKSPACE_ROOT not in sys.path:
        monkeypatch.syspath_prepend(WORKSPACE_ROOT)
    from nginx.generate_certs import generate_development_certificates
    import nginx.generate_certs as gen_mod

    test_certs_dir = str(tmp_path / "test_certs")
    test_cert_path = os.path.join(test_certs_dir, "server.crt")
    test_key_path = os.path.join(test_certs_dir, "server.key")

    monkeypatch.setattr(gen_mod, "CERTS_DIR", test_certs_dir)
    monkeypatch.setattr(gen_mod, "CERT_PATH", test_cert_path)
    monkeypatch.setattr(gen_mod, "KEY_PATH", test_key_path)

    # 1. Fresh generation
    generate_development_certificates()
    assert os.path.exists(test_cert_path)
    assert os.path.exists(test_key_path)

    # 2. Idempotent re-run
    mtime_cert_before = os.path.getmtime(test_cert_path)
    generate_development_certificates()
    mtime_cert_after = os.path.getmtime(test_cert_path)
    assert mtime_cert_before == mtime_cert_after
