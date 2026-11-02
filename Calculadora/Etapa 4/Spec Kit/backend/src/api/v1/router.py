from fastapi import APIRouter
from src.api.v1.schemas import CalculationRequest, CalculationResponse
from src.core.evaluator import evaluate_expression_full

api_router = APIRouter()

@api_router.post("/evaluate", response_model=CalculationResponse)
def evaluate(payload: CalculationRequest):
    """
    Evaluates a mathematical expression and returns the precise decimal result along with stack levels if RPN mode is selected.
    """
    result, stack_list = evaluate_expression_full(
        payload.expression,
        angle_unit=payload.angle_unit,
        mode=payload.mode
    )
    return CalculationResponse(
        expression=payload.expression,
        result=str(result),
        stack=stack_list if payload.mode == "rpn" else None
    )
