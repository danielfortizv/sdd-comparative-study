"""Application assembly for the Backend_Service (design "Application Assembly").

This module wires the FastAPI application together:

* Instantiates the :class:`~fastapi.FastAPI` app.
* Mounts the Evaluate_Endpoint router from :mod:`app.api.routes`.
* Configures CORS so the Vite dev server (and the deployed frontend) can call
  the endpoint from a different origin (supports Requirement 14.3).
* Registers exception handlers that translate both Evaluation_Engine domain
  errors and request-validation failures into the uniform ``ErrorResponse``
  shape with 4xx status codes (design "Error Handling"; Requirements 4.1-4.6,
  5.4, 5.6).

Error mapping (design Error Handling table)
-------------------------------------------
Every :class:`~app.engine.errors.EvaluationError` subclass
(``EmptyExpressionError``, ``InvalidCharacterError``, ``InvalidSyntaxError``,
``UnbalancedParenthesesError``, ``DivisionByZeroError``) maps to HTTP ``422``
with ``{"error": "<message>"}``.

Pydantic/request validation failures map to the same ``ErrorResponse`` shape so
the frontend contract stays uniform (Requirement 5.6, 13.5):

* A malformed JSON body (unparseable request) maps to HTTP ``400``.
* A missing field, wrong type, or an expression exceeding the 256-character
  maximum maps to HTTP ``422``.

No error path ever returns a ``result`` field (Requirement 5.5).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.api.schemas import ErrorResponse
from app.engine.errors import EvaluationError

#: Origins allowed to call the API. These cover the Vite dev server on its
#: default port (5173) and a common alternative (3000), on both ``localhost``
#: and the ``127.0.0.1`` loopback form.
ALLOWED_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

#: Uniform message for any request-body validation failure. It covers a missing
#: field, a wrong type, a malformed body, and an over-length expression so the
#: frontend sees a single, stable error shape (Requirements 5.6, 13.5).
_VALIDATION_MESSAGE = (
    "Request body is malformed or the expression exceeds the maximum length "
    "of 256 characters."
)

#: HTTP status codes used by the error handlers. Literals are used (rather than
#: ``fastapi.status`` constants) because the "422 Unprocessable" constant name
#: differs across FastAPI/Starlette versions; the numeric codes are stable.
_HTTP_400_BAD_REQUEST = 400
_HTTP_422_UNPROCESSABLE = 422


def _error_response(message: str, status_code: int) -> JSONResponse:
    """Build a :class:`~fastapi.responses.JSONResponse` carrying an ``ErrorResponse``.

    Args:
        message: The descriptive, human-readable error message.
        status_code: The 4xx HTTP status code to return.

    Returns:
        A JSON response whose body is ``{"error": message}`` and never
        contains a ``result`` field (Requirement 5.5).
    """
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=message).model_dump(),
    )


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application.

    Assembles the app, mounts the Evaluate_Endpoint router, enables CORS for
    the frontend origins, and registers the exception handlers that enforce the
    uniform ``ErrorResponse`` contract.

    Returns:
        The fully configured :class:`~fastapi.FastAPI` instance.
    """
    app = FastAPI(
        title="Web Calculator Backend",
        description=(
            "Exact-decimal PEMDAS expression evaluation over a single typed "
            "REST endpoint."
        ),
        version="0.1.0",
    )

    # CORS: allow the Vite dev server / deployed frontend to call the endpoint
    # cross-origin (supports Requirement 14.3). The API is a stateless math
    # oracle with no cookies/credentials, so credentials are not enabled.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.exception_handler(EvaluationError)
    async def _handle_evaluation_error(
        request: Request, exc: EvaluationError
    ) -> JSONResponse:
        """Map any Evaluation_Engine domain error to a 422 ``ErrorResponse``.

        Covers ``EmptyExpressionError``, ``InvalidCharacterError``,
        ``InvalidSyntaxError``, ``UnbalancedParenthesesError``, and
        ``DivisionByZeroError`` uniformly using each error's descriptive
        ``message`` (Requirements 4.1-4.6, 5.4).
        """
        return _error_response(exc.message, _HTTP_422_UNPROCESSABLE)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Map request/body validation failures to a uniform ``ErrorResponse``.

        A malformed (unparseable) JSON body is reported as HTTP ``400``; any
        other validation failure (missing field, wrong type, expression longer
        than 256 characters) is reported as HTTP ``422``. Both use the same
        ``ErrorResponse`` shape so the frontend contract stays uniform
        (Requirements 5.6, 13.5).
        """
        status_code = _HTTP_422_UNPROCESSABLE
        for err in exc.errors():
            if err.get("type") == "json_invalid":
                status_code = _HTTP_400_BAD_REQUEST
                break
        return _error_response(_VALIDATION_MESSAGE, status_code)

    return app


#: The ASGI application instance imported by the server (``uvicorn app.main:app``).
app = create_app()


__all__ = ["app", "create_app", "ALLOWED_ORIGINS"]
