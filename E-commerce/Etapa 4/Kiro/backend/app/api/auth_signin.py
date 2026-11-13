"""Authentication sign-in/sign-out API router.

Exposes ``POST /auth/login`` and ``POST /auth/logout`` over HTTP/JSON. The
router validates request shape, delegates to the sign-in service, and maps
outcomes to JSON responses with appropriate status codes. It contains no
business logic and never reaches the data store directly.

- ``POST /auth/login`` accepts ``identifier`` and ``password``; on complete,
  valid input it establishes an active ``Session`` and returns the session
  representation (Requirements 6.1, 6.9). On incomplete/invalid input it
  returns ``401 Unauthorized`` with a uniform authentication error that
  indicates failure without exposing internal detail, hashes, or submitted
  credential values (Requirements 6.3, 7.4). The ``password`` is never
  returned (Requirements 7.2, 7.3).
- ``POST /auth/logout`` ends the active ``Session`` (Requirement 6.6).
"""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.models.session import Session
from app.services.signin_service import AuthenticationError, sign_in, sign_out

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Sign-in request body carrying the credential contract.

    Both fields are typed as optional strings so that missing/empty values are
    handled by the service's uniform authentication failure rather than by a
    separate schema-validation error that could reveal field-level internals.
    The ``password`` is accepted only as input and is never echoed back.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    identifier: str | None = None
    password: str | None = None


def _session_body(session: Session) -> dict[str, object]:
    """Serialize a session for the HTTP response.

    The Stage 1 response shape is ``{active, customerId}``; the Stage 2
    moderator flag (Assumption A5) is added additively and only when it is
    ``True``, so a regular customer's login/logout response keeps the exact
    Stage 1 shape and inherited behavior is preserved (Requirement 9.5). The
    frontend reads ``isModerator`` from a moderator login to gate the
    moderation view.
    """
    body: dict[str, object] = {
        "active": session.active,
        "customerId": session.customer_id,
    }
    if session.is_moderator:
        body["isModerator"] = True
    return body


@router.post("/login")
def login(request: LoginRequest) -> JSONResponse:
    """Validate sign-in input and establish an active Session.

    Returns the active session body (``active`` + ``customerId``, plus
    ``isModerator`` only for a moderator) on success. On incomplete/invalid
    input returns ``401`` with a uniform error message.
    """
    try:
        session = sign_in(request.identifier or "", request.password or "")
    except AuthenticationError as error:
        # Uniform authentication failure; no internal detail, hash, or
        # submitted credential value is included (Requirements 6.3, 7.4).
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": str(error)},
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content=_session_body(session))


@router.post("/logout")
def logout() -> JSONResponse:
    """End the active Session, returning the resulting inactive session."""
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=_session_body(sign_out())
    )
