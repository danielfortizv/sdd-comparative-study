"""Identity service FastAPI app (Stage 4, port 18201).

Owns accounts and issues signed session tokens. Endpoints:

- ``POST /auth/register`` — create an account (Stage 3 parity).
- ``POST /auth/login`` — authenticate and return a signed token + session body.
- ``POST /auth/logout`` — return the inactive session body (tokens are
  stateless; the gateway drops the cookie/token binding).
- ``GET /internal/verify`` — verify a Bearer token and return its claims.
- ``GET /health`` — readiness.

Run with: ``uvicorn app.main:app --port 18201``.
"""

from __future__ import annotations

from fastapi import FastAPI, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.db import AccountStore
from app.service import (
    AuthenticationError,
    IdentifierTakenError,
    RegistrationError,
    register,
    seed_moderator,
    sign_in,
)
from contracts.tokens import issue_token, verify_token

store = AccountStore()
app = FastAPI(title="Stage 4 Identity Service", version="1.0.0")


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RegisterRequest(_CamelModel):
    identifier: str | None = None
    password: str | None = None


class LoginRequest(_CamelModel):
    identifier: str | None = None
    password: str | None = None


@app.on_event("startup")
def _seed() -> None:
    seed_moderator(store)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register_account(request: RegisterRequest) -> JSONResponse:
    try:
        account = register(request.identifier, request.password, store=store)
    except RegistrationError as error:
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
            content={"error": "identifier_taken", "message": error.message},
        )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"id": account.id, "identifier": account.identifier},
    )


@app.post("/auth/login")
def login(request: LoginRequest) -> JSONResponse:
    try:
        account = sign_in(
            request.identifier or "", request.password or "", store=store
        )
    except AuthenticationError as error:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": str(error)},
        )
    token = issue_token(account.id, account.identifier, account.is_moderator)
    body: dict[str, object] = {
        "active": True,
        "customerId": account.id,
        "token": token,
    }
    if account.is_moderator:
        body["isModerator"] = True
    return JSONResponse(status_code=status.HTTP_200_OK, content=body)


@app.post("/auth/logout")
def logout() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"active": False, "customerId": None},
    )


@app.get("/internal/verify")
def verify(authorization: str | None = Header(default=None)) -> JSONResponse:
    """Verify a Bearer token and return its claims (internal use)."""
    claims = _claims_from_header(authorization)
    if claims is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "invalid_token"},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "customerId": claims.customer_id,
            "identifier": claims.identifier,
            "isModerator": claims.is_moderator,
        },
    )


def _claims_from_header(authorization: str | None):
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return verify_token(authorization.split(" ", 1)[1].strip())
