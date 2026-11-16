# Stage 4 test isolation

Tests use pytest `tmp_path` SQLite files. They must never point `TEST_DB_PATH` at an inherited, production-like, or historical database. Existing `backend/tests/conftest.py` supplies ephemeral RSA/AES and HMAC test keys. Required environment names are `TEST_DB_PATH`, `BANK_STORAGE_KEY`, `AUDIT_SIGNING_KEY`, `AUDIT_ADMIN_KEY`, `BANK_PRIVATE_KEY_PATH`, and `BANK_PUBLIC_KEY_PATH`; values must be generated only for the test process and must not be committed or logged.

`stage4_baseline.py` creates a disposable E3-shaped COP fixture. `stage4_accounts.py` contains only the approved D-02 fixture values.
