import ast
import math
from decimal import Decimal, InvalidOperation
from src.api.v1.errors import CalculatorError

def evaluate_expression(expression: str, angle_unit: str = "radians") -> Decimal:
    """
    Safely parses and evaluates a scientific mathematical expression using AST and Python's decimal module,
    guaranteeing strict PEMDAS precedence and high-precision decimal operations.
    """
    cleaned = "".join(expression.split())  # Remove whitespaces for safety
    if not cleaned:
        raise CalculatorError("SYNTAX_ERROR", "The mathematical expression cannot be empty.")

    # Translate visual carets ^ to ** for Python AST power operator compatibility
    cleaned = cleaned.replace("^", "**")

    try:
        # Parse expression to AST with eval mode
        tree = ast.parse(cleaned, mode="eval")
    except SyntaxError as e:
        raise CalculatorError("SYNTAX_ERROR", f"Invalid mathematical syntax: {str(e)}")

    def _eval(node) -> Decimal:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        
        elif isinstance(node, ast.Constant):  # Python 3.8+
            if isinstance(node.value, (int, float)):
                return Decimal(str(node.value))
            raise CalculatorError("SYNTAX_ERROR", f"Unsupported literal value type: {type(node.value).__name__}")
        
        elif isinstance(node, ast.Num):  # Older Python fallback
            return Decimal(str(node.n))
        
        elif isinstance(node, ast.Name):
            name_id = node.id
            if name_id == "pi":
                return Decimal(f"{math.pi:.28g}").normalize()
            elif name_id == "e":
                return Decimal(f"{math.e:.28g}").normalize()
            raise CalculatorError("SYNTAX_ERROR", f"Unsupported mathematical constant or variable: {name_id}")
            
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise CalculatorError("SYNTAX_ERROR", "Unsupported function call structure.")
            
            func_name = node.func.id
            whitelisted_funcs = {"sin", "cos", "tan", "asin", "acos", "atan", "sqrt", "ln", "log10", "root"}
            if func_name not in whitelisted_funcs:
                raise CalculatorError("SYNTAX_ERROR", f"Unsupported mathematical function: {func_name}")
            
            # Evaluate all arguments recursively
            args = [_eval(arg) for arg in node.args]
            
            # Validate argument counts
            if func_name == "root":
                if len(args) != 2:
                    raise CalculatorError("SYNTAX_ERROR", "Function root(x, y) expects exactly 2 arguments.")
            else:
                if len(args) != 1:
                    raise CalculatorError("SYNTAX_ERROR", f"Function {func_name} expects exactly 1 argument.")
            
            try:
                if func_name == "sin":
                    val = float(args[0])
                    if angle_unit == "degrees":
                        val = math.radians(val)
                    res = math.sin(val)
                elif func_name == "cos":
                    val = float(args[0])
                    if angle_unit == "degrees":
                        val = math.radians(val)
                    res = math.cos(val)
                elif func_name == "tan":
                    val = float(args[0])
                    if angle_unit == "degrees":
                        val_rad = math.radians(val)
                        if abs(val % 180 - 90) < 1e-9:
                            raise CalculatorError("DOMAIN_ERROR", "Tangent is undefined at 90 degrees or odd multiples.")
                        res = math.tan(val_rad)
                    else:
                        if abs(math.cos(val)) < 1e-15:
                            raise CalculatorError("DOMAIN_ERROR", "Tangent is undefined at odd multiples of pi/2.")
                        res = math.tan(val)
                elif func_name == "asin":
                    val = float(args[0])
                    if val < -1.0 or val > 1.0:
                        raise CalculatorError("DOMAIN_ERROR", "Inverse trigonometric input must be between -1 and 1.")
                    res = math.asin(val)
                    if angle_unit == "degrees":
                        res = math.degrees(res)
                elif func_name == "acos":
                    val = float(args[0])
                    if val < -1.0 or val > 1.0:
                        raise CalculatorError("DOMAIN_ERROR", "Inverse trigonometric input must be between -1 and 1.")
                    res = math.acos(val)
                    if angle_unit == "degrees":
                        res = math.degrees(res)
                elif func_name == "atan":
                    val = float(args[0])
                    res = math.atan(val)
                    if angle_unit == "degrees":
                        res = math.degrees(res)
                elif func_name == "sqrt":
                    val = float(args[0])
                    if val < 0:
                        raise CalculatorError("DOMAIN_ERROR", "Cannot take the square root of a negative number.")
                    res = math.sqrt(val)
                elif func_name == "ln":
                    val = float(args[0])
                    if val <= 0:
                        raise CalculatorError("DOMAIN_ERROR", "Logarithm input must be strictly positive.")
                    res = math.log(val)
                elif func_name == "log10":
                    val = float(args[0])
                    if val <= 0:
                        raise CalculatorError("DOMAIN_ERROR", "Logarithm input must be strictly positive.")
                    res = math.log10(val)
                elif func_name == "root":
                    x = float(args[0])
                    y = float(args[1])
                    if y == 0:
                        raise CalculatorError("DIVISION_BY_ZERO", "Root degree cannot be zero.")
                    if x < 0:
                        if int(y) == y and int(y) % 2 == 0:
                            raise CalculatorError("DOMAIN_ERROR", "Even root of a negative number is undefined.")
                    res = x ** (1.0 / y)
                
                # Convert back to high-precision Decimal, normalized to strip floating noise
                res_dec = Decimal(f"{res:.28g}").normalize()
                return res_dec
            except CalculatorError:
                raise
            except OverflowError:
                raise CalculatorError("OVERFLOW", "The calculation resulted in an arithmetic overflow.")
            except Exception as e:
                raise CalculatorError("DOMAIN_ERROR", f"Mathematical domain error: {str(e)}")
        
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
                try:
                    return left_val / right_val
                except OverflowError:
                    raise CalculatorError("OVERFLOW", "Arithmetic division overflow.")
            elif isinstance(node.op, ast.Pow):
                try:
                    if left_val < 0 and right_val % 1 != 0:
                        raise CalculatorError("DOMAIN_ERROR", "Fractional power of a negative number is undefined.")
                    return left_val ** right_val
                except CalculatorError:
                    raise
                except (InvalidOperation, ValueError, TypeError):
                    raise CalculatorError("DOMAIN_ERROR", "Invalid or undefined power operation.")
                except OverflowError:
                    raise CalculatorError("OVERFLOW", "The power operation resulted in an arithmetic overflow.")
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
        if result == result.to_integral_value():
            return Decimal(result.to_integral_value())
        return result.normalize()
    except CalculatorError:
        raise
    except InvalidOperation as e:
        raise CalculatorError("SYNTAX_ERROR", f"Invalid arithmetic decimal operation: {str(e)}")
    except Exception as e:
        raise CalculatorError("SYNTAX_ERROR", f"Mathematical parsing error: {str(e)}")
