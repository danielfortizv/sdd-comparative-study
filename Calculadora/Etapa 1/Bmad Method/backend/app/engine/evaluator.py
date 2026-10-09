import ast
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
    }

    # Allowed unary operators mapped to Decimal operations
    UNARY_OPS = {
        ast.UAdd: lambda a: +a,
        ast.USub: lambda a: -a,
    }

    def evaluate(self, node: ast.AST) -> Decimal:
        # Evaluate within a local context to prevent modifying the global process context
        with localcontext() as ctx:
            ctx.prec = 28
            result = self.visit(node)
            if not isinstance(result, Decimal):
                raise TypeError(f"Evaluation resulted in unexpected type: {type(result).__name__}")
            return result

    def visit_Expression(self, node: ast.Expression):
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Decimal:
        # Boolean is a subclass of int in Python, so block booleans explicitly
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise TypeError(f"Unsupported constant type: {type(node.value).__name__}")
        # Convert floats to string first to prevent IEEE-754 binary conversion noise
        return Decimal(str(node.value))

    def visit_BinOp(self, node: ast.BinOp) -> Decimal:
        op_type = type(node.op)
        if op_type not in self.BIN_OPS:
            raise TypeError(f"Unsupported binary operator: {op_type.__name__}")
        
        left_val = self.visit(node.left)
        right_val = self.visit(node.right)
        
        # Division by zero will be intercepted natively or by decimal module
        return self.BIN_OPS[op_type](left_val, right_val)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Decimal:
        op_type = type(node.op)
        if op_type not in self.UNARY_OPS:
            raise TypeError(f"Unsupported unary operator: {op_type.__name__}")
        
        operand_val = self.visit(node.operand)
        return self.UNARY_OPS[op_type](operand_val)

    def generic_visit(self, node: ast.AST):
        """Block any syntax nodes that are not explicitly whitelisted."""
        raise ValueError(f"Error: Forbidden syntax node: {type(node).__name__}")
