"""Automated External Cryptographic Secrets Generator (E3-DEP-01, H6-02, H6-03).

Features:
1. Create-Only by Default (H6-03 Item 1):
   Refuses to overwrite an existing secrets file without explicit --force flag.
   Prevents silent key rotation and loss of persistent financial data.
2. Platform-Appropriate File Permissions (H6-03 Item 5):
   - On Windows: Uses icacls to strip inheritance and grant exclusive read/write to current user.
   - On POSIX: Sets mode 0600 (owner read/write).
3. Secret Hygiene:
   Values are never printed to console, command line, or build logs.

Safe Backup & Restoration Procedure (H6-03 Item 3):
---------------------------------------------------
1. Backup:
   Copy `deployment/docker.env` and `backend/certs/` to an encrypted, offline vault
   or hardware security module (HSM). Never commit secrets or unencrypted archives to source control.
2. Restoration:
   When moving to a new host or recovering from disaster:
   a. Restore `docker.env` into `deployment/docker.env`.
   b. Restore `bank_private.pem`, `bank_public.pem`, `localhost_cert.pem`, and `localhost_key.pem` into `backend/certs/`.
   c. Verify file permissions via `python scripts/generate_deployment_secrets.py --verify-permissions`.
   d. Launch stack via `docker compose -f deployment/docker-compose.yml up -d`.
3. Key Rotation Constraint:
   Symmetric storage keys (`BANK_STORAGE_KEY`) CANNOT be rotated by regenerating secrets;
   doing so causes immediate decryption failure (`InvalidTag`) on existing SQLite at-rest records.
   Key rotation requires an approved online re-encryption migration process.
"""

import argparse
import os
import secrets
import stat
import subprocess
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_ENV_TARGET = os.path.join(PROJECT_ROOT, "deployment", "docker.env")
EXAMPLE_ENV_TARGET = os.path.join(PROJECT_ROOT, "deployment", ".env.example")


def restrict_file_permissions(file_path: str) -> dict:
    """Enforces restrictive file permissions appropriate for the host operating system.

    On Windows: Uses icacls to remove inherited permissions and grant exclusive (RW) to current user.
    On POSIX: Uses os.chmod with mode 0600 (S_IRUSR | S_IWUSR).
    """
    abs_path = os.path.abspath(file_path)
    info = {"platform": sys.platform, "path": abs_path, "success": False, "method": ""}

    if sys.platform == "win32":
        user = os.environ.get("USERNAME")
        if user:
            try:
                # /inheritance:r removes all inherited permissions
                # /grant:r gives exclusive access without preserving broad inheritance
                res = subprocess.run(
                    ["icacls", abs_path, "/inheritance:r", "/grant:r", f"{user}:(R,W)"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                info["success"] = (res.returncode == 0)
                info["method"] = f"Windows icacls restricted to user '{user}' (RW)"
            except Exception as e:
                info["method"] = f"icacls failed: {e}"
        else:
            info["method"] = "USERNAME environment variable not found on Windows"
    else:
        try:
            os.chmod(abs_path, stat.S_IRUSR | stat.S_IWUSR)
            info["success"] = True
            info["method"] = "POSIX chmod 0600 (owner read/write only)"
        except Exception as e:
            info["method"] = f"chmod failed: {e}"

    return info


def generate_secrets_file(target_path: str = DEFAULT_ENV_TARGET, force: bool = False) -> str:
    """Generates strong cryptographic secrets and writes them to target file.

    By default, operates as CREATE-ONLY. Refuses to overwrite existing files to prevent
    accidental loss of persistent database encryption keys (H6-03 Item 1).
    """
    abs_target = os.path.abspath(target_path)
    os.makedirs(os.path.dirname(abs_target), exist_ok=True)

    if os.path.exists(abs_target) and not force:
        raise FileExistsError(
            f"Secrets file already exists at '{abs_target}'. "
            "Refusing to overwrite to prevent losing encryption keys for existing persistent data. "
            "Pass --force if you intentionally wish to replace existing secrets."
        )

    storage_key = secrets.token_hex(32)
    signing_key = secrets.token_urlsafe(32)
    admin_key = secrets.token_urlsafe(32)

    lines = [
        "# Shift Bank Stage 3 — Provisioned Local Deployment Secrets (H6-02, H6-03)",
        "# Generated securely via scripts/generate_deployment_secrets.py",
        "# NEVER commit this file or expose secret values in logs or images.",
        f"BANK_STORAGE_KEY={storage_key}",
        f"AUDIT_SIGNING_KEY={signing_key}",
        f"AUDIT_ADMIN_KEY={admin_key}",
        "ENVIRONMENT=production",
        "ENABLE_TEST_ENDPOINTS=false",
        "SHIFT_BANK_DATA_VOLUME=shift_bank_h6_data",
        "",
    ]

    with open(abs_target, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Apply platform-appropriate file access restrictions
    restrict_file_permissions(abs_target)

    return abs_target


def update_example_file(example_path: str = EXAMPLE_ENV_TARGET):
    """Updates .env.example with secure, non-reusable placeholders."""
    os.makedirs(os.path.dirname(os.path.abspath(example_path)), exist_ok=True)
    lines = [
        "# ==============================================================================",
        "# Shift Bank Stage 3 — External Cryptographic Environment Template (E3-DEP-01)",
        "# Copy to deployment/docker.env and configure strong secrets before launching.",
        "# Generate securely using: python scripts/generate_deployment_secrets.py",
        "# NEVER commit production secrets or private keys to source control.",
        "# ==============================================================================",
        "",
        "# 256-bit AES at-rest field encryption key (64 hex characters)",
        "BANK_STORAGE_KEY=SET_STRONG_64_HEX_CHAR_AES_KEY_HERE",
        "",
        "# HMAC-SHA256 audit ledger entry signing key (>= 32 bytes)",
        "AUDIT_SIGNING_KEY=SET_STRONG_32_BYTE_AUDIT_SIGNING_KEY_HERE",
        "",
        "# Administrative verification token for GET /api/audit/verify",
        "AUDIT_ADMIN_KEY=SET_STRONG_ADMIN_VERIFICATION_TOKEN_HERE",
        "",
        "# Environment identifier (production, staging, development)",
        "ENVIRONMENT=production",
        "",
        "# Guard for test-only simulation endpoints (strictly false in production)",
        "ENABLE_TEST_ENDPOINTS=false",
        "",
    ]
    with open(example_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate secure deployment environment secrets (Create-Only by Default)")
    parser.add_argument("--target", default=DEFAULT_ENV_TARGET, help="Output env file path (default: deployment/docker.env)")
    parser.add_argument("--force", action="store_true", help="Force overwrite of existing secrets file (WARNING: invalidates existing persistent databases)")
    parser.add_argument("--update-example", action="store_true", help="Also refresh .env.example placeholders")
    parser.add_argument("--verify-permissions", action="store_true", help="Enforce and display restrictive permissions on target file without modifying secrets")
    args = parser.parse_args()

    if args.verify_permissions:
        if not os.path.exists(args.target):
            print(f"Target file does not exist: {args.target}")
            sys.exit(1)
        perm_info = restrict_file_permissions(args.target)
        print(f"[SECURITY] Permission verification: {perm_info['method']} (Success: {perm_info['success']})")
        sys.exit(0)

    try:
        out_file = generate_secrets_file(args.target, force=args.force)
        perm_info = restrict_file_permissions(out_file)
        print(f"[SECURITY] Strong cryptographic secrets generated and securely written to: {out_file}")
        print(f"[SECURITY] Access restrictions: {perm_info['method']}. Secret values were NOT printed.")
    except FileExistsError as e:
        print(f"[PRESERVED] {e}")
        print("[PRESERVED] Existing secrets remain untouched to protect persistent data.")
        sys.exit(0)

    if args.update_example:
        update_example_file()
        print("[SECURITY] Updated deployment/.env.example with non-reusable placeholders.")
