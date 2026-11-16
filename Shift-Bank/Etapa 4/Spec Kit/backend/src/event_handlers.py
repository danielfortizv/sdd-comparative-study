"""Typed event validation and builders for Stage 4 monetary operations."""
from money import convert_minor


def validate_event_payload(event_type: str, payload: dict):
    if not isinstance(payload, dict):
        raise ValueError("Event payload must be an object")
    known = {"AccountOpeningBalanceSnapshot", "ReferenceAccountProvisioned", "LegacyHistoryImported",
             "InternalTransferCompleted", "CurrencyConversionCompleted", "InternalTransferMfaPending",
             "InternalTransferMfaResolved", "AchTransferMfaPending", "AchTransferMfaResolved", "AchTransferInitiated",
             "AchTransferSettled", "AchTransferFailed", "RecurringScheduleCreated",
             "RecurringSchedulePaused", "RecurringScheduleResumed", "RecurringScheduleCancelled", "RecurringScheduleMfaConfirmed",
             "RecurringExecutionCompleted", "RecurringExecutionFailed"}
    if event_type not in known:
        raise ValueError("Unknown event type")
    if event_type in ("AccountOpeningBalanceSnapshot", "ReferenceAccountProvisioned"):
        if not isinstance(payload.get("account_id"), str) or payload.get("currency") not in {"COP", "USD", "EUR", "GBP"}:
            raise ValueError("Invalid account opening event")
        if isinstance(payload.get("balance_minor"), bool) or not isinstance(payload.get("balance_minor"), int):
            raise ValueError("Opening balance must be integer minor units")
    elif event_type == "LegacyHistoryImported":
        if not isinstance(payload.get("history_id"), str) or isinstance(payload.get("amount_minor"), bool) or not isinstance(payload.get("amount_minor"), int):
            raise ValueError("Invalid legacy history event")
    elif event_type == "InternalTransferMfaPending":
        if not isinstance(payload.get("transfer_id"), str) or not isinstance(payload.get("amount_minor"), int) or payload.get("currency") not in {"COP","USD","EUR","GBP"}:
            raise ValueError("Invalid MFA pending event")
    elif event_type == "InternalTransferMfaResolved":
        if payload.get("outcome") not in {"COMPLETED","FAILED","EXPIRED"} or not isinstance(payload.get("transfer_id"), str):
            raise ValueError("Invalid MFA resolution event")
    elif event_type in {"AchTransferMfaPending", "AchTransferMfaResolved", "AchTransferInitiated", "AchTransferSettled", "AchTransferFailed",
                        "RecurringScheduleCreated", "RecurringSchedulePaused", "RecurringScheduleResumed",
                        "RecurringScheduleCancelled", "RecurringScheduleMfaConfirmed", "RecurringExecutionCompleted", "RecurringExecutionFailed"}:
        reference = payload.get("transfer_id") if event_type == "AchTransferMfaResolved" else payload.get("reference_id")
        if not isinstance(reference, str):
            raise ValueError("Operational event requires a stable reference")
        if "amount_minor" in payload and (isinstance(payload["amount_minor"], bool) or not isinstance(payload["amount_minor"], int)):
            raise ValueError("Operational event amount must be integer minor units")
        if "currency" in payload and payload["currency"] not in {"COP", "USD", "EUR", "GBP"}:
            raise ValueError("Operational event has unsupported currency")
    elif event_type in ("InternalTransferCompleted", "CurrencyConversionCompleted"):
        legs = payload.get("legs")
        if not isinstance(payload.get("transfer_id"), str) or not isinstance(legs, list) or len(legs) != 2:
            raise ValueError("Composite monetary event requires two legs")
        for leg in legs:
            if not isinstance(leg.get("account_id"), str) or leg.get("currency") not in {"COP", "USD", "EUR", "GBP"}:
                raise ValueError("Invalid account/currency event leg")
            for field in ("delta_minor", "version"):
                if isinstance(leg.get(field), bool) or not isinstance(leg.get(field), int):
                    raise ValueError("Event monetary values and versions must be integers")
            if leg["version"] < 1:
                raise ValueError("Event account version must be positive")
        if legs[0]["account_id"] == legs[1]["account_id"] or not legs[0]["delta_minor"] < 0 < legs[1]["delta_minor"]:
            raise ValueError("Invalid debit/credit event legs")
        if event_type == "InternalTransferCompleted":
            if legs[0]["currency"] != legs[1]["currency"] or legs[0]["delta_minor"] + legs[1]["delta_minor"] != 0:
                raise ValueError("Internal transfer must conserve same-currency value")
        else:
            src, dst = legs
            calculated, numerator, denominator = convert_minor(-src["delta_minor"], src["currency"], dst["currency"])
            if dst["delta_minor"] != calculated or payload.get("rate_numerator") != numerator or payload.get("rate_denominator") != denominator:
                raise ValueError("Conversion rate/result invariant failed")
    return payload


def internal_transfer_legs(source_id, destination_id, currency, amount, source_version, destination_version):
    return [
        {"account_id": source_id, "delta_minor": -amount, "currency": currency, "version": source_version + 1},
        {"account_id": destination_id, "delta_minor": amount, "currency": currency, "version": destination_version + 1},
    ]


def conversion_legs(source_id, destination_id, source_currency, destination_currency, source_amount,
                    destination_amount, source_version, destination_version):
    return [
        {"account_id": source_id, "delta_minor": -source_amount, "currency": source_currency, "version": source_version + 1},
        {"account_id": destination_id, "delta_minor": destination_amount, "currency": destination_currency, "version": destination_version + 1},
    ]
