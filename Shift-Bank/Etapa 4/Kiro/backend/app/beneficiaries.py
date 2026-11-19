"""Reglas de beneficiarios ACH: validación de formato y enmascarado (Etapa 2, Tarea 19).

Autoridad de servicio sobre el formato (ACH-03): routing = exactamente 9 dígitos numéricos;
cuenta = 4–17 dígitos numéricos. El enmascarado (D05) expone solo los últimos 4 dígitos de la
cuenta; el routing (identificador público de banco) no se enmascara (F14).
"""

from __future__ import annotations

import re


class BeneficiaryError(Exception):
    """Error de validación de beneficiario con `code` estable para el mapeo a HTTP."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


_ROUTING_RE = re.compile(r"^\d{9}$")
_ACCOUNT_RE = re.compile(r"^\d{4,17}$")


def validate_routing(routing: str) -> None:
    if not isinstance(routing, str) or not _ROUTING_RE.match(routing):
        raise BeneficiaryError("INVALID_ROUTING",
                               "El número de routing debe tener exactamente 9 dígitos numéricos")


def validate_account_number(account: str) -> None:
    if not isinstance(account, str) or not _ACCOUNT_RE.match(account):
        raise BeneficiaryError("INVALID_ACCOUNT_NUMBER",
                               "El número de cuenta debe tener entre 4 y 17 dígitos numéricos")


def validate_fields(*, name: str, bank: str, routing_number: str, account_number: str) -> None:
    """Valida los campos obligatorios y el formato (ACH-03)."""
    if not (name and name.strip()):
        raise BeneficiaryError("INVALID_BENEFICIARY", "El nombre del beneficiario es obligatorio")
    if not (bank and bank.strip()):
        raise BeneficiaryError("INVALID_BENEFICIARY", "El banco del beneficiario es obligatorio")
    validate_routing(routing_number)
    validate_account_number(account_number)


def mask_account(account_number: str) -> str:
    """Enmascara el número de cuenta dejando visibles solo los últimos 4 dígitos (D05)."""
    last4 = account_number[-4:] if account_number else ""
    return "••••" + last4


def public_view(*, name: str, bank: str, account_number: str, routing_number: str) -> dict:
    """Representación pública de un beneficiario: cuenta enmascarada; routing visible (F14)."""
    return {
        "name": name,
        "bank": bank,
        "routing_number": routing_number,
        "account_masked": mask_account(account_number),
    }
