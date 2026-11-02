import decimal
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from app.calculator import evaluate_expression, evaluate_postfix, CalculatorError

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
    angle_unit: str = Field("radians", description="Angle unit for trig functions: 'radians' or 'degrees'")
    mode: str = Field("standard", description="Evaluation mode: 'standard' or 'rpn'")
    stack: list[str] = Field(default_factory=list, description="The current active evaluation stack in RPN Mode")

class EvaluateResponse(BaseModel):
    expression: str
    result: str
    stack: list[str] = Field(default_factory=list, description="The updated RPN stack state")

@app.post("/api/v1/evaluate", response_model=EvaluateResponse, status_code=status.HTTP_200_OK)
def evaluate(request: EvaluateRequest):
    try:
        if request.mode == "standard":
            # Perform standard mathematical evaluation using our exact decimal parser
            result = evaluate_expression(request.expression, request.angle_unit)
            return EvaluateResponse(
                expression=request.expression,
                result=f"{result:f}",
                stack=[]
            )
        elif request.mode == "rpn":
            # Parse the incoming stack strings into decimal.Decimal objects
            initial_stack = []
            for item in request.stack:
                try:
                    initial_stack.append(decimal.Decimal(item))
                except (decimal.InvalidOperation, ValueError, TypeError):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid value on stack: {item}"
                    )
            
            # Tokenize the expression as space-separated tokens
            tokens = request.expression.strip().split()
            
            # Evaluate directly on the stack
            final_stack = evaluate_postfix(tokens, request.angle_unit, initial_stack)
            
            # Format results back to strings using exact textual decimal representations
            stack_strs = [f"{item:f}" for item in final_stack]
            result_str = stack_strs[-1] if stack_strs else "0"
            
            return EvaluateResponse(
                expression=request.expression,
                result=result_str,
                stack=stack_strs
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported evaluation mode: {request.mode}"
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
