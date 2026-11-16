from fractions import Fraction

import pytest
from money import convert_minor, from_minor, parse_amount, requires_mfa, to_minor, usd_equivalent_minor
import sqlite3
import database
import pytest
from fastapi import HTTPException
from services import _stage4_policy
import sqlite3
import database
import pytest
from fastapi import HTTPException
from services import _stage4_policy


def test_fixed_rational_pairs_and_half_up():
    assert convert_minor(10000, "USD", "EUR") == (9000, 9, 10)
    assert convert_minor(10000, "USD", "GBP") == (8000, 8, 10)
    assert convert_minor(9000, "EUR", "USD") == (10000, 10, 9)
    assert convert_minor(8000, "GBP", "USD") == (10000, 10, 8)
    assert convert_minor(10000, "EUR", "GBP") == (8889, 8, 9)
    assert convert_minor(10000, "GBP", "EUR") == (11250, 9, 8)
    assert convert_minor(1, "USD", "EUR")[0] == 1


def test_plain_decimal_only_and_cop_has_no_fx():
    assert to_minor(parse_amount("12.30")) == 1230
    assert from_minor(1230).as_tuple().exponent == -2
    for bad in ("1e2", "NaN", "1.001", "0.00", "-1.00"):
        with pytest.raises(ValueError):
            parse_amount(bad)
    with pytest.raises(ValueError):
        convert_minor(100, "COP", "USD")


def test_mfa_policy_exact_boundaries_and_usd_equivalent():
    assert not requires_mfa(100000, "USD")
    assert requires_mfa(100001, "USD")
    assert not requires_mfa(90000, "EUR")
    assert requires_mfa(90001, "EUR")
    assert not requires_mfa(100000, "COP")
    assert requires_mfa(100000000, "COP")
    assert usd_equivalent_minor(90001, "EUR") == Fraction(900010, 9)


@pytest.mark.parametrize("account_id,at_cap,over_cap", [
    ("acc_checking_123", 500_000_000, 500_000_001),
    ("CHK-1001", 500_000, 500_001),
    ("EUR-3001", 450_000, 450_001),
    ("GBP-4001", 400_000, 400_001),
])
def test_operation_limit_exact_equality_allowed(tmp_path, account_id, at_cap, over_cap):
    path = str(tmp_path / f"limits-{account_id}.sqlite")
    database.init_db(path)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    row = cursor.execute("SELECT currency FROM accounts WHERE id=?", (account_id,)).fetchone()
    account = {"id": account_id, "currency": row[0]}
    assert _stage4_policy(cursor, account, at_cap) in (True, False)
    with pytest.raises(HTTPException) as exc:
        _stage4_policy(cursor, account, over_cap)
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "LIMIT_EXCEEDED"
    conn.close()


@pytest.mark.parametrize("account_id,at_cap,over_cap", [
    ("acc_checking_123", 500_000_000, 500_000_001),
    ("CHK-1001", 500_000, 500_001),
    ("EUR-3001", 450_000, 450_001),
    ("GBP-4001", 400_000, 400_001),
])
def test_operation_limit_exact_equality_allowed(tmp_path, account_id, at_cap, over_cap):
    path = str(tmp_path / f"limits-{account_id}.sqlite")
    database.init_db(path)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    row = cursor.execute("SELECT currency FROM accounts WHERE id=?", (account_id,)).fetchone()
    account = {"id": account_id, "currency": row[0]}
    assert _stage4_policy(cursor, account, at_cap) in (True, False)
    with pytest.raises(HTTPException) as exc:
        _stage4_policy(cursor, account, over_cap)
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "LIMIT_EXCEEDED"
    conn.close()
