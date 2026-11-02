from typing import Literal
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import decimal
from decimal import Decimal
from backend.app.engine.evaluator import tokenize, infix_to_postfix, evaluate_postfix, RPNEvaluationError

router = APIRouter(prefix="/api/v1")

class EvaluateRequest(BaseModel):
    expression: str = Field(..., description="The mathematical expression or postfix token sequence to evaluate")
    angle_unit: Literal["radians", "degrees"] = Field("radians", description="The angle unit system to use for trigonometric evaluations")
    stack: list[str] = Field(default_factory=list, description="The current state of the evaluation stack represented as strings")
    expr_format: Literal["infix", "postfix"] = Field("infix", description="The formatting system of the input expression")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "expression": "12.5 + 3 * (4 - 1.5) / 2",
                    "angle_unit": "radians",
                    "stack": [],
                    "expr_format": "infix"
                },
                {
                    "expression": "+",
                    "angle_unit": "radians",
                    "stack": ["10", "20"],
                    "expr_format": "postfix"
                }
            ]
        }
    }

class EvaluateResponse(BaseModel):
    status: Literal["success"] = Field("success", description="The status of the evaluation")
    expression: str = Field(..., description="The original evaluated expression")
    result: str = Field(..., description="The mathematically exact calculated decimal result represented as a string")
    stack: list[str] = Field(default_factory=list, description="The current state of the evaluation stack represented as strings")

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
        # Parse initial stack values securely to high-precision decimals
        decimal_stack = [Decimal(val) for val in payload.stack]
    except Exception as err:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "error_type": "invalid_stack",
                "message": f"Error: Invalid stack value: {str(err)}"
            }
        )

    try:
        tokens = tokenize(payload.expression)
        if payload.expr_format == "postfix":
            postfix_tokens = tokens
        else:
            if not tokens:
                raise ValueError("Error: Expression is empty")
            postfix_tokens = infix_to_postfix(tokens)
            
        updated_stack = evaluate_postfix(postfix_tokens, initial_stack=decimal_stack, angle_unit=payload.angle_unit)
        
        # If in infix mode and no initial stack is passed, we expect exactly 1 final evaluation result
        if payload.expr_format == "infix" and not payload.stack and len(updated_stack) > 1:
            raise ValueError("Error: Invalid syntax structure")
            
        result_str = str(updated_stack[-1]) if updated_stack else "0"
        
        return EvaluateResponse(
            expression=payload.expression,
            result=result_str,
            stack=[str(v) for v in updated_stack]
        )
    except (ZeroDivisionError, decimal.DivisionByZero) as err:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "error_type": "division_by_zero",
                "message": "Error: Division by zero"
            }
        )
    except (TypeError, ValueError, RPNEvaluationError) as err:
        err_msg = str(err)
        error_type = "invalid_expression"
        if "division by zero" in err_msg.lower():
            error_type = "division_by_zero"
        elif "unbalanced parentheses" in err_msg.lower():
            error_type = "unbalanced_parentheses"
        elif "stack underflow" in err_msg.lower():
            error_type = "stack_underflow"
        elif "empty" in err_msg.lower():
            error_type = "empty_expression"
            
        # Standardize standard syntax errors under standard code
        if "stack underflow" in err_msg.lower() and payload.expr_format == "infix":
            err_msg = "Error: Invalid syntax structure"
            error_type = "invalid_expression"
            
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "error_type": error_type,
                "message": err_msg if err_msg.startswith("Error: ") else f"Error: {err_msg}"
            }
        )
    except Exception as err:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "error_type": "evaluation_failed",
                "message": f"Error: Evaluation failed: {str(err)}"
            }
        )
