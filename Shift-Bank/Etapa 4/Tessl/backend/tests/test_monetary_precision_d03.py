import json
import uuid
from decimal import Decimal, ROUND_HALF_UP
import pytest
from fastapi.testclient import TestClient
from backend.app.models import Account, AuditLog
from backend.app.services.audit_service import verify_audit_chain
from backend.app.services.fx_service import calculate_conversion, get_usd_equivalent


def test_precision_values_small_decimals(client: TestClient):
    """Test transfer and ACH with critical decimal values such as 0.10, 0.29, and 0.05 (D-03)."""
    accounts = client.get("/api/accounts").json()
    chk = next(a for a in accounts if a["account_number"] == "CHK-1001")
    sav = next(a for a in accounts if a["account_number"] == "SAV-2001")

    # 1. Transfer 0.10
    resp_010 = client.post(
        "/api/transfers",
        json={
            "from_account_id": chk["id"],
            "to_account_id": sav["id"],
            "amount": 0.10,
            "expected_from_version": chk["version"],
            "expected_to_version": sav["version"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp_010.status_code == 200
    assert resp_010.json()["amount"] == "0.10"

    chk = client.get(f"/api/accounts/{chk['id']}").json()
    sav = client.get(f"/api/accounts/{sav['id']}").json()
    assert chk["balance"] == "2499.90"
    assert sav["balance"] == "10000.10"

    # 2. Transfer 0.29 (famous binary floating-point representation issue)
    resp_029 = client.post(
        "/api/transfers",
        json={
            "from_account_id": chk["id"],
            "to_account_id": sav["id"],
            "amount": 0.29,
            "expected_from_version": chk["version"],
            "expected_to_version": sav["version"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp_029.status_code == 200
    assert resp_029.json()["amount"] == "0.29"

    chk = client.get(f"/api/accounts/{chk['id']}").json()
    sav = client.get(f"/api/accounts/{sav['id']}").json()
    assert chk["balance"] == "2499.61"
    assert sav["balance"] == "10000.39"

    # 3. Transfer 0.05
    resp_005 = client.post(
        "/api/transfers",
        json={
            "from_account_id": chk["id"],
            "to_account_id": sav["id"],
            "amount": 0.05,
            "expected_from_version": chk["version"],
            "expected_to_version": sav["version"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp_005.status_code == 200
    assert resp_005.json()["amount"] == "0.05"

    chk = client.get(f"/api/accounts/{chk['id']}").json()
    sav = client.get(f"/api/accounts/{sav['id']}").json()
    assert chk["balance"] == "2499.56"
    assert sav["balance"] == "10000.44"

    # 4. Amounts exceeding 2 decimal places must be rejected with HTTP 422
    for bad_amt in [0.295, 0.051, 0.1001]:
        resp_bad = client.post(
            "/api/transfers",
            json={
                "from_account_id": chk["id"],
                "to_account_id": sav["id"],
                "amount": bad_amt,
                "expected_from_version": chk["version"],
                "expected_to_version": sav["version"],
            },
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
        assert resp_bad.status_code == 422


def test_half_up_rounding_boundaries_fx():
    """Test precise half-up rounding boundaries and exact rounding residuals in FX calculations (D-03)."""
    # 1. 0.04 EUR -> USD (rate 10/9)
    # unrounded = 0.04 * 10 / 9 = 0.0444444444... rounds down to 0.04
    dest_amt, rate_disp, num, den, residual = calculate_conversion(Decimal("0.04"), "EUR", "USD")
    assert dest_amt == Decimal("0.04")
    assert num == 10 and den == 9
    assert rate_disp == Decimal("1.1111111111")
    expected_residual_1 = (Decimal("0.04") - (Decimal("0.04") * Decimal(10) / Decimal(9))).quantize(
        Decimal("0.0000000001"), rounding=ROUND_HALF_UP
    )
    assert residual == expected_residual_1
    assert abs(residual) <= Decimal("0.005")

    # 2. 0.05 EUR -> USD (rate 10/9)
    # unrounded = 0.05 * 10 / 9 = 0.0555555555... rounds up to 0.06
    dest_amt, rate_disp, num, den, residual = calculate_conversion(Decimal("0.05"), "EUR", "USD")
    assert dest_amt == Decimal("0.06")
    assert num == 10 and den == 9
    expected_residual_2 = (Decimal("0.06") - (Decimal("0.05") * Decimal(10) / Decimal(9))).quantize(
        Decimal("0.0000000001"), rounding=ROUND_HALF_UP
    )
    assert residual == expected_residual_2
    assert abs(residual) <= Decimal("0.005")

    # 3. Exact boundary: 0.04 GBP -> EUR (rate 9/8 = 1.125)
    # 0.04 * 9 / 8 = 0.36 / 8 = 0.0450000000...
    # In ROUND_HALF_UP, 0.045 rounds UP to 0.05
    dest_amt, rate_disp, num, den, residual = calculate_conversion(Decimal("0.04"), "GBP", "EUR")
    assert dest_amt == Decimal("0.05")
    assert num == 9 and den == 8
    assert rate_disp == Decimal("1.1250000000")
    assert residual == Decimal("0.0050000000")

    # 4. 0.02 GBP -> EUR: 0.02 * 9 / 8 = 0.0225 -> rounds down to 0.02
    dest_amt, rate_disp, num, den, residual = calculate_conversion(Decimal("0.02"), "GBP", "EUR")
    assert dest_amt == Decimal("0.02")
    assert residual == Decimal("-0.0025000000")


def test_repeated_calculations_no_floating_point_drift(client: TestClient):
    """Test 10 consecutive transfers of 0.29 without accumulated floating-point drift (D-03)."""
    accounts = client.get("/api/accounts").json()
    chk = next(a for a in accounts if a["account_number"] == "CHK-1001")
    sav = next(a for a in accounts if a["account_number"] == "SAV-2001")

    chk_initial_balance = Decimal(str(chk["balance"]))
    sav_initial_balance = Decimal(str(sav["balance"]))

    amount_step = Decimal("0.29")
    iterations = 10

    for i in range(iterations):
        chk_curr = client.get(f"/api/accounts/{chk['id']}").json()
        sav_curr = client.get(f"/api/accounts/{sav['id']}").json()

        resp = client.post(
            "/api/transfers",
            json={
                "from_account_id": chk["id"],
                "to_account_id": sav["id"],
                "amount": float(amount_step),
                "expected_from_version": chk_curr["version"],
                "expected_to_version": sav_curr["version"],
            },
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
        assert resp.status_code == 200
        assert resp.json()["amount"] == "0.29"

    # Total transferred: exactly 10 * 0.29 = 2.90
    expected_chk = chk_initial_balance - (amount_step * iterations)
    expected_sav = sav_initial_balance + (amount_step * iterations)

    chk_final = client.get(f"/api/accounts/{chk['id']}").json()
    sav_final = client.get(f"/api/accounts/{sav['id']}").json()

    assert chk_final["balance"] == f"{expected_chk:.2f}"
    assert sav_final["balance"] == f"{expected_sav:.2f}"
    assert chk_final["balance"] == "2497.10"
    assert sav_final["balance"] == "10002.90"


def test_exact_json_serialization_and_audit_preservation(client: TestClient, db_session):
    """Verify exact decimal string serialization on API responses and audit log entries (D-03, D-11)."""
    accounts = client.get("/api/accounts").json()
    chk = next(a for a in accounts if a["account_number"] == "CHK-1001")
    sav = next(a for a in accounts if a["account_number"] == "SAV-2001")

    # 1. Check account balances are strings
    assert isinstance(chk["balance"], str)
    assert chk["balance"] == "2500.00"

    # 2. Check limits API responses are strings
    limits = client.get("/api/limits").json()
    assert isinstance(limits["per_transaction_limit"], str)
    assert isinstance(limits["daily_limit"], str)
    assert isinstance(limits["current_daily_total"], str)
    assert isinstance(limits["remaining_daily_limit"], str)
    assert limits["per_transaction_limit"] == "5000.00"
    assert limits["daily_limit"] == "10000.00"

    # 3. Check MFA status API threshold is string
    mfa = client.get("/api/mfa/status").json()
    assert isinstance(mfa["threshold"], str)
    assert mfa["threshold"] == "1000.00"

    # 4. Perform a transfer of 125.50 and verify API and audit details
    trf_resp = client.post(
        "/api/transfers",
        json={
            "from_account_id": chk["id"],
            "to_account_id": sav["id"],
            "amount": 125.50,
            "expected_from_version": chk["version"],
            "expected_to_version": sav["version"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert trf_resp.status_code == 200
    data = trf_resp.json()
    assert isinstance(data["amount"], str)
    assert data["amount"] == "125.50"

    # Verify latest audit log entry
    latest_audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.event_type == "transfer_internal")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert latest_audit is not None
    audit_details = json.loads(latest_audit.details)
    assert audit_details["amount"] == "125.50"
    assert isinstance(audit_details["amount"], str)

    # Verify audit chain integrity with HMAC
    chain_result = verify_audit_chain(db_session)
    assert chain_result["valid"] is True


def test_cross_currency_and_inverse_rate_exactness(client: TestClient):
    """Test rational arithmetic round-trip and inverse rate precision without float drift (D-03)."""
    accounts = client.get("/api/accounts").json()
    usd_acc = next(a for a in accounts if a["currency"] == "USD")
    eur_acc = next(a for a in accounts if a["currency"] == "EUR")

    # Convert 100.00 USD -> EUR: rate is 9/10 -> exactly 90.00 EUR
    resp_forward = client.post(
        "/api/conversions",
        json={
            "from_account_id": usd_acc["id"],
            "to_account_id": eur_acc["id"],
            "source_amount": 100.00,
            "expected_from_version": usd_acc["version"],
            "expected_to_version": eur_acc["version"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp_forward.status_code == 200
    f_data = resp_forward.json()
    assert f_data["source_amount"] == "100.00"
    assert f_data["destination_amount"] == "90.00"
    assert f_data["rate_numerator"] == 9
    assert f_data["rate_denominator"] == 10
    assert f_data["exchange_rate_display"] == "0.9000000000"
    assert f_data["rounding_residual"] == "0.0000000000"

    eur_updated = client.get(f"/api/accounts/{eur_acc['id']}").json()
    usd_updated = client.get(f"/api/accounts/{usd_acc['id']}").json()

    # Convert 90.00 EUR -> USD: rate is 10/9 -> exactly 100.00 USD (90 * 10 / 9 = 100.00)
    resp_inverse = client.post(
        "/api/conversions",
        json={
            "from_account_id": eur_acc["id"],
            "to_account_id": usd_acc["id"],
            "source_amount": 90.00,
            "expected_from_version": eur_updated["version"],
            "expected_to_version": usd_updated["version"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp_inverse.status_code == 200
    i_data = resp_inverse.json()
    assert i_data["source_amount"] == "90.00"
    assert i_data["destination_amount"] == "100.00"
    assert i_data["rate_numerator"] == 10
    assert i_data["rate_denominator"] == 9
    assert i_data["exchange_rate_display"] == "1.1111111111"
    assert i_data["rounding_residual"] == "0.0000000000"

    # Perfect round-trip: balances returned to original values
    usd_final = client.get(f"/api/accounts/{usd_acc['id']}").json()
    eur_final = client.get(f"/api/accounts/{eur_acc['id']}").json()
    assert usd_final["balance"] == usd_acc["balance"]
    assert eur_final["balance"] == eur_acc["balance"]
