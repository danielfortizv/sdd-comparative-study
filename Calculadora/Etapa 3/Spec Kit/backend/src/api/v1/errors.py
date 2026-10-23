from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    error: str
    details: str

class CalculatorError(Exception):
    def __init__(self, error_code: str, details: str, status_code: int = 400):
        self.error_code = error_code
        self.details = details
        self.status_code = status_code
        super().__init__(details)

async def calculator_error_handler(request: Request, exc: CalculatorError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error_code, "details": exc.details}
    )
