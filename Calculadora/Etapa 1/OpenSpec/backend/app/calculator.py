import ast
import decimal

# Configure Decimal precision and behavior
decimal.getcontext().prec = 28

class CalculatorError(ValueError):
    pass

def evaluate_ast_node(node) -> decimal.Decimal:
    if isinstance(node, ast.Expression):
        return evaluate_ast_node(node.body)
    
    elif isinstance(node, ast.Constant):
        try:
            # Converting to string preserves exact textual decimal value for floats (e.g. str(0.1) == '0.1')
            return decimal.Decimal(str(node.value))
        except (decimal.InvalidOperation, TypeError, ValueError):
            raise CalculatorError(f"Invalid constant: {node.value}")
            
    elif isinstance(node, ast.BinOp):
        left = evaluate_ast_node(node.left)
        right = evaluate_ast_node(node.right)
        
        if isinstance(node.op, ast.Add):
            return left + right
        elif isinstance(node.op, ast.Sub):
            return left - right
        elif isinstance(node.op, ast.Mult):
            return left * right
        elif isinstance(node.op, ast.Div):
            if right == decimal.Decimal('0'):
                raise CalculatorError("Division by zero")
            return left / right
        else:
            raise CalculatorError(f"Unsupported binary operator: {type(node.op).__name__}")
            
    elif isinstance(node, ast.UnaryOp):
        operand = evaluate_ast_node(node.operand)
        if isinstance(node.op, ast.USub):
            return -operand
        elif isinstance(node.op, ast.UAdd):
            return +operand
        else:
            raise CalculatorError(f"Unsupported unary operator: {type(node.op).__name__}")
            
    else:
        raise CalculatorError("Invalid expression syntax")

def evaluate_expression(expr: str) -> decimal.Decimal:
    expr = expr.strip()
    if not expr:
        raise CalculatorError("Expression cannot be empty")
        
    # Strictly validate allowed characters
    allowed_chars = set("0123456789.+-*/() ")
    if not all(c in allowed_chars for c in expr):
        raise CalculatorError("Invalid characters in expression")
        
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise CalculatorError("Malformed expression or mismatched parentheses")
        
    try:
        result = evaluate_ast_node(tree)
        # Normalize to strip trailing zeros and avoid scientific notation for standard displays where possible
        normalized = result.normalize()
        # If normalizing results in scientific notation (e.g., 1E-28), format it nicely
        # But for general cases, normalized works perfectly
        return normalized
    except CalculatorError:
        raise
    except ZeroDivisionError:
        raise CalculatorError("Division by zero")
    except Exception as e:
        raise CalculatorError(f"Error evaluating expression: {str(e)}")
