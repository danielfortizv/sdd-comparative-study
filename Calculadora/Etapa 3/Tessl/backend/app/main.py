from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal
from decimal import Decimal
from app.calculator import evaluate_expression

app = FastAPI(
    title="High-Precision Web Calculator API",
    description="A robust, PEMDAS-compliant arithmetic and scientific calculation backend",
    version="2.0.0"
)

# Configure CORS to allow frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the exact origin(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvaluateRequest(BaseModel):
    operation: str = Field(..., description="The arithmetic/scientific expression to evaluate")
    angle_unit: Literal["radians", "degrees"] = Field("radians", description="The angle unit for trigonometric functions")

class EvaluateResponse(BaseModel):
    result: float = Field(..., description="The numeric result of the evaluation")

@app.post(
    "/api/v1/evaluate",
    response_model=EvaluateResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate an arithmetic or scientific expression"
)
async def evaluate(request: EvaluateRequest):
    expression = request.operation
    angle_unit = request.angle_unit
    
    try:
        decimal_result = evaluate_expression(expression, angle_unit)
        
        # Check for non-finite values (Infinity/NaN)
        if decimal_result.is_infinite() or decimal_result.is_nan():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "math error",
                    "message": "Calculation resulted in an undefined or out-of-range value"
                }
            )
            
        # Convert Decimal to float for JSON response serialization
        return EvaluateResponse(result=float(decimal_result))
        
    except ZeroDivisionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "math error",
                "message": "Division by zero is not allowed"
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "syntax error",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "server error",
                "message": f"An unexpected system error occurred: {str(e)}"
            }
        )
