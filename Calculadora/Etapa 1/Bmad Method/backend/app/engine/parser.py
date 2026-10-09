import ast
import decimal
from backend.app.engine.evaluator import SafeMathEvaluator

class MathEvaluationError(ValueError):
    """Custom domain exception raised for mathematical evaluation or syntax errors."""
    pass

def safe_parse_and_evaluate(expression: str) -> decimal.Decimal:
    """Parses a mathematical expression string into a Python AST and evaluates it safely

    using a custom safe visitor pattern.
    
    All mathematical, syntax, and whitelisting exceptions are caught and wrapped
    into a standardized MathEvaluationError domain exception.
    """
    if not isinstance(expression, str):
        raise MathEvaluationError("Error: Input expression must be a string")
        
    cleaned_expr = expression.strip()
    if not cleaned_expr:
        raise MathEvaluationError("Error: Expression is empty")
    
    try:
        # ast.parse with mode='eval' compiles strictly as a single evaluation expression,
        # never as multiple statements. This is highly secure.
        tree = ast.parse(cleaned_expr, mode='eval')
    except SyntaxError as err:
        error_msg = str(err).lower()
        if "unmatched" in error_msg or "never closed" in error_msg or "unclosed" in error_msg:
            raise MathEvaluationError("Error: Unbalanced parentheses") from err
        raise MathEvaluationError("Error: Invalid syntax structure") from err
        
    evaluator = SafeMathEvaluator()
    try:
        return evaluator.evaluate(tree)
    except (ZeroDivisionError, decimal.DivisionByZero) as err:
        raise MathEvaluationError("Error: Division by zero") from err
    except (TypeError, ValueError) as err:
        err_msg = str(err)
        # Preserve whitelisting syntax node errors
        if "Error: Forbidden syntax node" in err_msg:
            raise MathEvaluationError(err_msg) from err
        raise MathEvaluationError(f"Error: Invalid expression: {err_msg}") from err
    except Exception as err:
        raise MathEvaluationError(f"Error: Evaluation failed: {str(err)}") from err
