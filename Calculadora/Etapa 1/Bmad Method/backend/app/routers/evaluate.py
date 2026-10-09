from typing import Literal
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from backend.app.engine.parser import safe_parse_and_evaluate, MathEvaluationError

router = APIRouter(prefix="/api/v1")

class EvaluateRequest(BaseModel):
    expression: str = Field(..., description="The mathematical expression to evaluate", example="12.5 + 3 * (4 - 1.5) / 2")

class EvaluateResponse(BaseModel):
    status: Literal["success"] = Field("success", description="The status of the evaluation")
    expression: str = Field(..., description="The original evaluated expression")
    result: str = Field(..., description="The mathematically exact calculated decimal result represented as a string")

class ErrorResponse(BaseModel):
    status: Literal["error"] = Field("error", description="The status of the error")
    error_type: str = Field(..., description="The specific classification code of the mathematical error")
    message: str = Field(..., description="The formatted user-facing error message starting with 'Error: '")

@router.post(
    "/evaluate",
    response_model=EvaluateResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Unprocessable mathematical or syntactical expression"}
    }
)
async def evaluate_expression(payload: EvaluateRequest):
    try:
        result_decimal = safe_parse_and_evaluate(payload.expression)
        return EvaluateResponse(
            expression=payload.expression,
            result=str(result_decimal)
        )
    except MathEvaluationError as err:
        err_msg = str(err)
        # Determine specific error classification token
        error_type = "invalid_expression"
        if "division by zero" in err_msg.lower():
            error_type = "division_by_zero"
        elif "unbalanced parentheses" in err_msg.lower():
            error_type = "unbalanced_parentheses"
        elif "empty" in err_msg.lower():
            error_type = "empty_expression"
            
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "error_type": error_type,
                "message": err_msg
            }
        )
