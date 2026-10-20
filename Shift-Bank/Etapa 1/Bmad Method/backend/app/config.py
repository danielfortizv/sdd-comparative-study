from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "shift_bank.db"

# Mock Identity (AD-4)
DEFAULT_MOCK_CUSTOMER_ID = "cust_mock_001"
DEFAULT_MOCK_CUSTOMER_NAME = "Alex Morgan"
DEFAULT_MOCK_CUSTOMER_EMAIL = "alex.morgan@example.com"

# Sensitive Transfer & Security Parameters (AD-3, AD-6)
SENSITIVE_TRANSFER_THRESHOLD_CENTS = 100000  # $1,000.00 in cents
MFA_TTL_SECONDS = 300  # 5 minutes
MFA_MAX_ATTEMPTS = 3
UNIVERSAL_MOCK_OTP = "123456"

# Concurrency & Idempotency (AD-5)
IDEMPOTENCY_CACHE_TTL_SECONDS = 60
