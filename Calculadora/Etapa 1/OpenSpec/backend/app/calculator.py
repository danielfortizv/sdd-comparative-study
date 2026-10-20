import ast
import decimal
import math

# Configure Decimal precision and behavior
decimal.getcontext().prec = 28

# Set up physical math constants
PI = decimal.Decimal("3.1415926535897932384626433832795")
E_CONST = decimal.Decimal("2.7182818284590452353602874713527")

class CalculatorError(ValueError):
    pass

def evaluate_ast_node(node, angle_unit: str = "radians") -> decimal.Decimal:
    if isinstance(node, ast.Expression):
        return evaluate_ast_node(node.body, angle_unit)
    
    elif isinstance(node, ast.Constant):
        try:
            # Converting to string preserves exact textual decimal value for floats
            return decimal.Decimal(str(node.value))
        except (decimal.InvalidOperation, TypeError, ValueError):
            raise CalculatorError(f"Invalid constant: {node.value}")
            
    elif isinstance(node, ast.Name):
        # Physical constants
        if node.id == "pi":
            return PI
        elif node.id == "e":
            return E_CONST
        else:
            raise CalculatorError(f"Undefined variable: {node.id}")
            
    elif isinstance(node, ast.BinOp):
        left = evaluate_ast_node(node.left, angle_unit)
        right = evaluate_ast_node(node.right, angle_unit)
        
        try:
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
            elif isinstance(node.op, ast.Pow):
                if left == decimal.Decimal('0') and right < decimal.Decimal('0'):
                    raise CalculatorError("Division by zero")
                return left ** right
            else:
                raise CalculatorError(f"Unsupported binary operator: {type(node.op).__name__}")
        except CalculatorError:
            raise
        except decimal.DivisionByZero:
            raise CalculatorError("Division by zero")
        except (decimal.InvalidOperation, ArithmeticError, ValueError, TypeError):
            raise CalculatorError("Math domain error")
            
    elif isinstance(node, ast.UnaryOp):
        operand = evaluate_ast_node(node.operand, angle_unit)
        if isinstance(node.op, ast.USub):
            return -operand
        elif isinstance(node.op, ast.UAdd):
            return +operand
        else:
            raise CalculatorError(f"Unsupported unary operator: {type(node.op).__name__}")
            
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise CalculatorError("Invalid function syntax")
            
        func_name = node.func.id
        allowed_functions = {"sin", "cos", "tan", "asin", "acos", "atan", "ln", "log10", "sqrt", "root"}
        if func_name not in allowed_functions:
            raise CalculatorError(f"Unsupported function: {func_name}")
            
        args = [evaluate_ast_node(arg, angle_unit) for arg in node.args]
        
        # Argument count validation
        if func_name == "root":
            if len(args) != 2:
                raise CalculatorError("root() requires exactly 2 arguments (base, degree)")
        else:
            if len(args) != 1:
                raise CalculatorError(f"{func_name}() requires exactly 1 argument")
                
        try:
            # Handle native decimal functions
            if func_name == "sqrt":
                x = args[0]
                if x < decimal.Decimal('0'):
                    raise CalculatorError("Math domain error")
                return x.sqrt()
                
            elif func_name == "ln":
                x = args[0]
                if x <= decimal.Decimal('0'):
                    raise CalculatorError("Math domain error")
                return x.ln()
                
            elif func_name == "log10":
                x = args[0]
                if x <= decimal.Decimal('0'):
                    raise CalculatorError("Math domain error")
                return x.log10()
                
            elif func_name == "root":
                x, y = args[0], args[1]
                if y == decimal.Decimal('0'):
                    raise CalculatorError("Division by zero")
                # Evaluate root as fraction exponent: x ** (1 / y)
                exponent = decimal.Decimal("1") / y
                if x < decimal.Decimal('0') and (y % decimal.Decimal('2') == decimal.Decimal('0')):
                    raise CalculatorError("Math domain error")
                return x ** exponent
                
            # Handle trigonometric/inverse-trigonometric functions via float mapping
            elif func_name in {"sin", "cos", "tan", "asin", "acos", "atan"}:
                f_val = float(args[0])
                
                if func_name in {"sin", "cos", "tan"}:
                    r = math.radians(f_val) if angle_unit == "degrees" else f_val
                    
                    if func_name == "sin":
                        res = math.sin(r)
                    elif func_name == "cos":
                        res = math.cos(r)
                    elif func_name == "tan":
                        if abs(math.cos(r)) < 1e-15:
                            raise CalculatorError("Math domain error")
                        res = math.tan(r)
                        
                else: # Inverse trig functions
                    if func_name in {"asin", "acos"} and abs(f_val) > 1.0:
                        raise CalculatorError("Math domain error")
                        
                    if func_name == "asin":
                        res = math.asin(f_val)
                    elif func_name == "acos":
                        res = math.acos(f_val)
                    elif func_name == "atan":
                        res = math.atan(f_val)
                        
                    if angle_unit == "degrees":
                        res = math.degrees(res)
                        
                # Round to 15 decimal places to clean up float anomalies (e.g. sin(pi) -> 0.0)
                rounded_res = round(res, 15)
                return decimal.Decimal(str(rounded_res))
                
            else:
                raise CalculatorError(f"Unsupported function: {func_name}")
                
        except CalculatorError:
            raise
        except ZeroDivisionError:
            raise CalculatorError("Division by zero")
        except (decimal.InvalidOperation, ArithmeticError, ValueError, TypeError):
            raise CalculatorError("Math domain error")
            
    else:
        raise CalculatorError("Invalid expression syntax")

def evaluate_expression(expr: str, angle_unit: str = "radians") -> decimal.Decimal:
    expr = expr.strip()
    if not expr:
        raise CalculatorError("Expression cannot be empty")
        
    # Strictly validate allowed characters: numerals, operators, parentheses, commas, whitespace, and alphabetical function characters
    allowed_chars = set("0123456789.+-*/(), abcdefghijklmnopqrstuvwxyz")
    if not all(c in allowed_chars for c in expr):
        raise CalculatorError("Invalid characters in expression")
        
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise CalculatorError("Malformed expression or mismatched parentheses")
        
    try:
        result = evaluate_ast_node(tree, angle_unit)
        # Normalize to strip trailing zeros and avoid scientific notation for standard displays
        normalized = result.normalize()
        return normalized
    except CalculatorError:
        raise
    except ZeroDivisionError:
        raise CalculatorError("Division by zero")
    except Exception as e:
        raise CalculatorError(f"Error evaluating expression: {str(e)}")
