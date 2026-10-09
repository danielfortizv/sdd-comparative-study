from pydantic import BaseModel, Field

class CalculationRequest(BaseModel):
    expression: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The mathematical arithmetic expression to evaluate (e.g., 0.1 + 0.2)",
        example="12.5 + 3 * (4 - 1.5) / 2"
    )

class CalculationResponse(BaseModel):
    expression: str = Field(..., description="The original evaluated mathematical expression")
    result: str = Field(..., description="The highly precise computed decimal result")
