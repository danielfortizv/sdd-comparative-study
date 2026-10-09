import ast
from decimal import Decimal, InvalidOperation
from src.api.v1.errors import CalculatorError

def evaluate_expression(expression: str) -> Decimal:
    """
    Safely parses and evaluates an arithmetic expression using AST and Python's decimal module,
    guaranteeing strict PEMDAS precedence and high-precision decimal operations.
    """
    cleaned = "".join(expression.split()) # Remove whitespaces for safety
    if not cleaned:
        raise CalculatorError("SYNTAX_ERROR", "The mathematical expression cannot be empty.")

    try:
        # Parse expression to AST with eval mode
        tree = ast.parse(cleaned, mode="eval")
    except SyntaxError as e:
        raise CalculatorError("SYNTAX_ERROR", f"Invalid mathematical syntax: {str(e)}")

    def _eval(node) -> Decimal:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        
        elif isinstance(node, ast.Constant): # Python 3.8+
            # Handle float or integer constants and cast directly to Decimal
            if isinstance(node.value, (int, float)):
                return Decimal(str(node.value))
            raise CalculatorError("SYNTAX_ERROR", f"Unsupported literal value type: {type(node.value).__name__}")
        
        elif isinstance(node, ast.Num): # Older Python fallback
            return Decimal(str(node.n))
        
        elif isinstance(node, ast.BinOp):
            left_val = _eval(node.left)
            right_val = _eval(node.right)
            
            if isinstance(node.op, ast.Add):
                return left_val + right_val
            elif isinstance(node.op, ast.Sub):
                return left_val - right_val
            elif isinstance(node.op, ast.Mult):
                return left_val * right_val
            elif isinstance(node.op, ast.Div):
                if right_val == Decimal("0"):
                    raise CalculatorError("DIVISION_BY_ZERO", "Cannot divide a decimal number by exactly zero.")
                return left_val / right_val
            elif isinstance(node.op, ast.Pow):
                # Standard pow can result in floats, cast to prevent floating precision anomalies
                try:
                    # Enforce strict decimal-friendly power conversions
                    return left_val ** right_val
                except Exception as e:
                    raise CalculatorError("SYNTAX_ERROR", f"Error during power evaluation: {str(e)}")
            else:
                raise CalculatorError("SYNTAX_ERROR", f"Unsupported binary operator: {type(node.op).__name__}")
                
        elif isinstance(node, ast.UnaryOp):
            operand_val = _eval(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand_val
            elif isinstance(node.op, ast.USub):
                return -operand_val
            else:
                raise CalculatorError("SYNTAX_ERROR", f"Unsupported unary operator: {type(node.op).__name__}")
                
        else:
            raise CalculatorError("SYNTAX_ERROR", f"Unsupported mathematical structure or variable access: {type(node).__name__}")

    try:
        result = _eval(tree)
        # Normalize trailing zeros (e.g. 0.3000 -> 0.3) for aesthetic clean outputs
        if result == result.to_integral_value():
            return Decimal(result.to_integral_value())
        return result.normalize()
    except CalculatorError:
        raise
    except InvalidOperation as e:
        raise CalculatorError("SYNTAX_ERROR", f"Invalid arithmetic decimal operation: {str(e)}")
    except Exception as e:
        raise CalculatorError("SYNTAX_ERROR", f"Mathematical parsing error: {str(e)}")
