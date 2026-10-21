import ast
import math
import decimal
from decimal import Decimal, localcontext

class SafeMathEvaluator(ast.NodeVisitor):
    """Custom NodeVisitor that safely evaluates mathematical expression trees
    using arbitrary-precision Decimal arithmetic.
    """
    # Allowed binary operators mapped to Decimal operations
    BIN_OPS = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b,
        ast.Pow: lambda a, b: a ** b,
    }

    # Allowed unary operators mapped to Decimal operations
    UNARY_OPS = {
        ast.UAdd: lambda a: +a,
        ast.USub: lambda a: -a,
    }

    # Whitelisted scientific functions
    WHITELISTED_FUNCS = {
        "sin", "cos", "tan",
        "asin", "acos", "atan",
        "sqrt", "ln", "log", "log10"
    }

    def __init__(self, angle_unit: str = "radians"):
        super().__init__()
        self.angle_unit = angle_unit.lower()
        if self.angle_unit not in ("radians", "degrees"):
            raise ValueError("Error: Angle unit must be 'radians' or 'degrees'")

    def evaluate(self, node: ast.AST) -> Decimal:
        # Evaluate within a local context to prevent modifying the global process context
        with localcontext() as ctx:
            ctx.prec = 28
            result = self.visit(node)
            if not isinstance(result, Decimal):
                raise TypeError(f"Evaluation resulted in unexpected type: {type(result).__name__}")
            # Normalize trailing decimal zeros cleanly (e.g. 5.0000 -> 5)
            # but keep it if it is a fractional decimal.
            try:
                if result == result.to_integral_value():
                    return result.to_integral_value()
                return result.normalize()
            except Exception:
                return result

    def visit_Expression(self, node: ast.Expression):
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Decimal:
        # Boolean is a subclass of int in Python, so block booleans explicitly
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise TypeError(f"Unsupported constant type: {type(node.value).__name__}")
        # Convert floats to string first to prevent IEEE-754 binary conversion noise
        return Decimal(str(node.value))

    def visit_Name(self, node: ast.Name) -> Decimal:
        name_id = node.id.lower()
        if name_id == "pi":
            return Decimal("3.141592653589793238462643383")
        elif name_id == "e":
            return Decimal("2.718281828459045235360287471")
        raise ValueError(f"Error: Forbidden name constant: {node.id}")

    def visit_BinOp(self, node: ast.BinOp) -> Decimal:
        op_type = type(node.op)
        if op_type not in self.BIN_OPS:
            raise TypeError(f"Unsupported binary operator: {op_type.__name__}")

        left_val = self.visit(node.left)
        right_val = self.visit(node.right)

        # Custom domain bounds validation for exponents
        if op_type == ast.Pow:
            # Under-the-hood, fractional powers of negative numbers produce complex results
            if left_val < 0 and right_val % 1 != 0:
                raise ValueError("Error: Fractional power of a negative number is undefined")
            # Enforce division by zero bounds for negative powers
            if left_val == 0 and right_val < 0:
                raise ValueError("Error: Division by zero in power operation")

        # Division by zero will be intercepted natively or by decimal module
        return self.BIN_OPS[op_type](left_val, right_val)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Decimal:
        op_type = type(node.op)
        if op_type not in self.UNARY_OPS:
            raise TypeError(f"Unsupported unary operator: {op_type.__name__}")

        operand_val = self.visit(node.operand)
        return self.UNARY_OPS[op_type](operand_val)

    def visit_Call(self, node: ast.Call) -> Decimal:
        # Prevent calling methods or attributes: node.func must be a simple ast.Name node
        if not isinstance(node.func, ast.Name):
            raise ValueError("Error: Forbidden function call syntax")

        func_name = node.func.id.lower()
        if func_name not in self.WHITELISTED_FUNCS:
            raise ValueError(f"Error: Forbidden function call: {node.func.id}")

        # Enforce that all scientific functions accept exactly 1 argument
        if len(node.args) != 1:
            raise ValueError(f"Error: Function '{node.func.id}' expects exactly 1 argument")

        arg_val = self.visit(node.args[0])

        # Mathematical Domain validations
        if func_name == "sqrt":
            if arg_val < 0:
                raise ValueError("Error: Square root of a negative number is undefined")
            return arg_val.sqrt()

        if func_name in ("ln", "log", "log10"):
            if arg_val <= 0:
                raise ValueError("Error: Logarithm of zero or a negative number is undefined")
            if func_name == "ln":
                return arg_val.ln()
            else:
                return arg_val.log10()

        # Trigonometric Operations
        return self._eval_trig(func_name, arg_val)

    def _eval_trig(self, func_name: str, x: Decimal) -> Decimal:
        if func_name in ("sin", "cos", "tan"):
            # Angle units conversion prior to calculations
            if self.angle_unit == "degrees":
                pi = Decimal("3.141592653589793238462643383")
                x_rad = x * pi / Decimal("180")
            else:
                x_rad = x

            try:
                val_float = float(x_rad)
            except Exception as err:
                raise ValueError(f"Error: Invalid float value: {str(err)}")

            if func_name == "sin":
                res = math.sin(val_float)
            elif func_name == "cos":
                res = math.cos(val_float)
            elif func_name == "tan":
                # Intercept vertical asymptote (cos is near zero)
                cos_val = math.cos(val_float)
                if abs(cos_val) < 1e-15:
                    raise ValueError("Error: Tangent undefined at this angle")
                res = math.tan(val_float)

            # Avoid float formatting noise (like -0.0)
            if abs(res) < 1e-15:
                res = 0.0

            return Decimal(f"{res:.15g}")

        elif func_name in ("asin", "acos", "atan"):
            try:
                val_float = float(x)
            except Exception as err:
                raise ValueError(f"Error: Invalid float value: {str(err)}")

            # Domain boundary validations
            if func_name in ("asin", "acos") and (val_float < -1.0 or val_float > 1.0):
                raise ValueError("Error: Inverse trigonometric function domain is [-1, 1]")

            if func_name == "asin":
                res_rad = math.asin(val_float)
            elif func_name == "acos":
                res_rad = math.acos(val_float)
            elif func_name == "atan":
                res_rad = math.atan(val_float)

            res_dec = Decimal(f"{res_rad:.15g}")

            # Angle units conversion on inverse trig outputs
            if self.angle_unit == "degrees":
                pi = Decimal("3.141592653589793238462643383")
                res_dec = res_dec * Decimal("180") / pi

            # Clean output conversion
            final_float = float(res_dec)
            if abs(final_float) < 1e-15:
                final_float = 0.0
            return Decimal(f"{final_float:.15g}")

        raise ValueError(f"Error: Unknown trigonometric function '{func_name}'")

    def generic_visit(self, node: ast.AST):
        """Block any syntax nodes that are not explicitly whitelisted."""
        raise ValueError(f"Error: Forbidden syntax node: {type(node).__name__}")
