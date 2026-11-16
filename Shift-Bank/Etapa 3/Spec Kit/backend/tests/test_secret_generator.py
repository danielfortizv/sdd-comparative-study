"""Automated tests for external secrets generator create-only behavior and key continuity (H6-03 Item 1, 5).

Verifies that:
1. generate_secrets_file creates a new secrets file when absent.
2. generate_secrets_file refuses to overwrite an existing file when force=False (create-only guard).
3. generate_secrets_file allows overwrite only when force=True.
4. Restrictive permissions are enforced appropriately per platform.
"""

import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts")))

from generate_deployment_secrets import generate_secrets_file, restrict_file_permissions


def test_create_only_refusal_when_file_exists(tmp_path):
    """H6-03 Item 1: Refuses to overwrite existing secrets file unless force=True."""
    target_file = str(tmp_path / "test_docker.env")

    # 1. First creation succeeds
    created_path = generate_secrets_file(target_file, force=False)
    assert os.path.exists(created_path)

    with open(created_path, "r", encoding="utf-8") as f:
        initial_content = f.read()

    assert "BANK_STORAGE_KEY=" in initial_content
    assert "AUDIT_SIGNING_KEY=" in initial_content

    # 2. Second creation without force raises FileExistsError and preserves content
    with pytest.raises(FileExistsError) as exc_info:
        generate_secrets_file(target_file, force=False)

    assert "Refusing to overwrite" in str(exc_info.value)

    with open(created_path, "r", encoding="utf-8") as f:
        assert f.read() == initial_content

    # 3. Third creation with force=True succeeds
    forced_path = generate_secrets_file(target_file, force=True)
    assert forced_path == created_path


def test_restrict_file_permissions_execution(tmp_path):
    """H6-03 Item 5: Verifies platform permission enforcement runs successfully."""
    dummy_file = str(tmp_path / "dummy.env")
    with open(dummy_file, "w", encoding="utf-8") as f:
        f.write("TEST=1\n")

    info = restrict_file_permissions(dummy_file)
    assert info["success"] is True
    assert len(info["method"]) > 0
