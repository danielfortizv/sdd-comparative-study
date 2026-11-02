import decimal
from decimal import Decimal
from backend.app.engine.evaluator import tokenize, infix_to_postfix, evaluate_postfix, RPNEvaluationError

class MathEvaluationError(ValueError):
    """Custom domain exception raised for mathematical evaluation or syntax errors."""
    pass

def safe_parse_and_evaluate(expression: str, angle_unit: str = "radians") -> decimal.Decimal:
    """Parses a mathematical expression string, converts it to postfix RPN,

    and evaluates it safely using a stack-based evaluator. All mathematical, syntax, 
    and whitelisting exceptions are caught and wrapped into a standardized 
    MathEvaluationError domain exception.
    """
    if not isinstance(expression, str):
        raise MathEvaluationError("Error: Input expression must be a string")
        
    cleaned_expr = expression.strip()
    if not cleaned_expr:
        raise MathEvaluationError("Error: Expression is empty")
    
    try:
        tokens = tokenize(cleaned_expr)
        if not tokens:
            raise MathEvaluationError("Error: Expression is empty")
            
        postfix = infix_to_postfix(tokens)
        stack = evaluate_postfix(postfix, angle_unit=angle_unit)
        
        if len(stack) > 1:
            raise MathEvaluationError("Error: Invalid syntax structure")
        elif not stack:
            raise MathEvaluationError("Error: Evaluation resulted in unexpected empty stack")
            
        return stack[0]
    except (ZeroDivisionError, decimal.DivisionByZero) as err:
        raise MathEvaluationError("Error: Division by zero") from err
    except (TypeError, ValueError, RPNEvaluationError) as err:
        err_msg = str(err)
        # Map syntax issues (like stack underflow) in standard mode to invalid syntax structure
        if "stack underflow" in err_msg.lower():
            raise MathEvaluationError("Error: Invalid syntax structure") from err
        # Keep custom power-operation division by zero distinct from basic division by zero
        if "division by zero" in err_msg.lower() and "power operation" not in err_msg.lower():
            raise MathEvaluationError("Error: Division by zero") from err
        if "unbalanced parentheses" in err_msg.lower():
            raise MathEvaluationError("Error: Unbalanced parentheses") from err
        if "forbidden" in err_msg.lower():
            raise MathEvaluationError(err_msg) from err
        raise MathEvaluationError(err_msg) from err
    except Exception as err:
        raise MathEvaluationError(f"Error: Evaluation failed: {str(err)}") from err
