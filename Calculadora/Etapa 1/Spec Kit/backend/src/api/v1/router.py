from fastapi import APIRouter
from src.api.v1.schemas import CalculationRequest, CalculationResponse
from src.core.evaluator import evaluate_expression

api_router = APIRouter()

@api_router.post("/evaluate", response_model=CalculationResponse)
def evaluate(payload: CalculationRequest):
    """
    Evaluates a mathematical expression and returns the precise decimal result.
    """
    result = evaluate_expression(payload.expression)
    return CalculationResponse(
        expression=payload.expression,
        result=str(result)
    )
