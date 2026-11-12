"""Registration endpoint (API layer).

Exposes ``POST /auth/register`` for the credential contract (``identifier`` +
``password``). It validates request shape, delegates to the registration
service, and returns JSON responses with appropriate status codes.

On success it returns the created account's public identity only — never the
password and never the stored ``passwordHash`` (Requirements 7.2, 7.3). On
failure it returns a structured JSON error that names each empty required item
and each non-conforming item (Requirements 5.3, 5.4) and that never echoes any
submitted credential value (Requirements 5.5, 7.4).

This router lives in its own module so the authentication feature can be built
incrementally without colliding with the sign-in/sign-out work. It is included
additively by ``app.main``.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.services.registration_service import (
    IdentifierTakenError,
    RegistrationError,
    register,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


class RegisterRequest(BaseModel):
    """Registration request body for the credential contract.

    The ``password`` is accepted only as input here; it is never stored or
    returned as readable plain text (Requirements 7.2, 7.3). Fields are typed
    as optional text so that missing or empty items reach the service layer,
    which is the single place that classifies offending items (R5.3, R5.4).
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    identifier: str | None = None
    password: str | None = None


class RegisterResponse(BaseModel):
    """Successful registration response.

    Carries only the created account's public identity. It intentionally omits
    the password and the stored ``passwordHash`` so no credential value is ever
    returned (Requirements 7.2, 7.3).
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str
    identifier: str


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
)
def register_account(request: RegisterRequest) -> RegisterResponse:
    """Create a ``Customer`` account from valid registration input.

    Returns 201 with the new account's public identity on success. Returns 422
    with a structured error naming the offending items on validation failure,
    or 409 when the identifier is already taken. No response ever contains a
    submitted credential value or a stored hash.
    """
    try:
        customer = register(request.identifier, request.password)
    except RegistrationError as error:
        # Structured validation error: name the offending items only, never
        # the submitted credential values (R5.3, R5.4, R5.5).
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": error.message,
                "emptyFields": error.empty_fields,
                "nonConformingFields": error.non_conforming_fields,
            },
        )
    except IdentifierTakenError as error:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "identifier_taken",
                "message": error.message,
            },
        )

    return RegisterResponse(id=customer.id, identifier=customer.identifier)
