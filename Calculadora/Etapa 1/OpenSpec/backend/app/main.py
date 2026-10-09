from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from app.calculator import evaluate_expression, CalculatorError

app = FastAPI(title="Web Calculator API", version="1.0.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvaluateRequest(BaseModel):
    expression: str = Field(..., description="The mathematical expression to evaluate")

class EvaluateResponse(BaseModel):
    expression: str
    result: str

@app.post("/api/v1/evaluate", response_model=EvaluateResponse, status_code=status.HTTP_200_OK)
def evaluate(request: EvaluateRequest):
    try:
        # Perform mathematical evaluation using our exact decimal parser
        result = evaluate_expression(request.expression)
        return EvaluateResponse(
            expression=request.expression,
            result=f"{result:f}"
        )
    except CalculatorError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
