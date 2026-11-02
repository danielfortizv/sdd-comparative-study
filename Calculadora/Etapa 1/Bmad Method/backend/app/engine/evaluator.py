import decimal
from decimal import Decimal, localcontext
import re
import math

class RPNEvaluationError(ValueError):
    """Custom exception raised for RPN stack evaluation errors."""
    pass

def tokenize(expression: str) -> list[str]:
    """Tokenize a mathematical expression string into individual elements.

    Handles numbers, operators, functions, and brackets.
    """
    if not isinstance(expression, str):
        raise TypeError("Error: Input expression must be a string")
        
    # Replace display multiplication/division symbols for user convenience
    expr_cleaned = expression.replace("×", "*").replace("÷", "/")
    
    # Regex to capture:
    # 1. Floating-point and integer numbers (e.g., 12.5, 3, .5)
    # 2. Multi-char and single-char operators and brackets: **, ^, +, -, *, /, (, ), ,
    # 3. Word identifiers for functions and constants: sin, cos, pi, e, etc.
    pattern = r'(?:[0-9]+\.?[0-9]*|\.[0-9]+)|\*\*|\^|[\+\-\*/\(\),]|[a-zA-Z_][a-zA-Z0-9_]*'
    
    tokens = re.findall(pattern, expr_cleaned)
    return tokens

def infix_to_postfix(tokens: list[str]) -> list[str]:
    """Converts infix mathematical tokens to postfix (RPN) tokens

    using the Shunting Yard Algorithm.
    """
    # Define operator precedence and associativity
    prec = {
        'u+': 4, 'u-': 4,
        '**': 4, '^': 4,
        '*': 3, '/': 3,
        '+': 2, '-': 2,
    }
    
    # Right-associative operators
    right_assoc = {'u+', 'u-', '**', '^'}
    
    # Whitelisted functions and constants
    whitelisted_funcs = {
        "sin", "cos", "tan",
        "asin", "acos", "atan",
        "sqrt", "ln", "log", "log10"
    }
    
    output = []
    op_stack = []
    
    expect_operand = True
    
    for token in tokens:
        # 1. Number
        if re.match(r'^[0-9.]', token):
            output.append(token)
            expect_operand = False
        # 2. Constants
        elif token.lower() in ("pi", "e"):
            output.append(token.lower())
            expect_operand = False
        # 3. Functions
        elif token.lower() in whitelisted_funcs:
            op_stack.append(token.lower())
            expect_operand = True
        # 4. Comma
        elif token == ',':
            while op_stack and op_stack[-1] != '(':
                output.append(op_stack.pop())
            if not op_stack:
                raise ValueError("Error: Unbalanced parentheses or misplaced comma")
            expect_operand = True
        # 5. Operators
        elif token in ('+', '-', '*', '/', '**', '^'):
            op = token
            # Map ^ to ** for internal consistency
            if op == '^':
                op = '**'
            # Determine if unary
            if op in ('+', '-'):
                if expect_operand:
                    op = 'u' + op  # 'u+' or 'u-'
            
            while op_stack:
                top = op_stack[-1]
                if top == '(':
                    break
                # If top is a function, it has higher precedence than any binary operator
                if top in whitelisted_funcs:
                    output.append(op_stack.pop())
                    continue
                # Compare precedence
                if top in prec:
                    if (prec[top] > prec[op]) or (prec[top] == prec[op] and op not in right_assoc):
                        output.append(op_stack.pop())
                        continue
                break
            
            op_stack.append(op)
            expect_operand = True
        # 6. Left Parenthesis
        elif token == '(':
            op_stack.append('(')
            expect_operand = True
        # 7. Right Parenthesis
        elif token == ')':
            while op_stack and op_stack[-1] != '(':
                output.append(op_stack.pop())
            if not op_stack:
                raise ValueError("Error: Unbalanced parentheses")
            op_stack.pop()  # Pop '('
            # If function is on top, pop and add to output
            if op_stack and op_stack[-1] in whitelisted_funcs:
                output.append(op_stack.pop())
            expect_operand = False
        else:
            raise ValueError(f"Error: Forbidden token: {token}")
            
    while op_stack:
        top = op_stack.pop()
        if top in ('(', ')'):
            raise ValueError("Error: Unbalanced parentheses")
        output.append(top)
        
    return output

def _eval_binop(op: str, left: Decimal, right: Decimal) -> Decimal:
    """Safely evaluates basic binary operations using exact Decimal math."""
    if op == '+':
        return left + right
    elif op == '-':
        return left - right
    elif op == '*':
        return left * right
    elif op == '/':
        if right == 0:
            raise ZeroDivisionError("Error: Division by zero")
        return left / right
    elif op in ('**', '^'):
        # Enforce power-specific domain bounds
        if left < 0 and right % 1 != 0:
            raise ValueError("Error: Fractional power of a negative number is undefined")
        if left == 0 and right < 0:
            raise ValueError("Error: Division by zero in power operation")
        return left ** right
    else:
        raise ValueError(f"Error: Unknown binary operator: {op}")

def _eval_func(func_name: str, arg_val: Decimal, angle_unit: str) -> Decimal:
    """Safely evaluates unary mathematical functions with domain checks."""
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
    if func_name in ("sin", "cos", "tan"):
        if angle_unit == "degrees":
            pi = Decimal("3.141592653589793238462643383")
            x_rad = arg_val * pi / Decimal("180")
        else:
            x_rad = arg_val

        try:
            val_float = float(x_rad)
        except Exception as err:
            raise ValueError(f"Error: Invalid float value: {str(err)}")

        if func_name == "sin":
            res = math.sin(val_float)
        elif func_name == "cos":
            res = math.cos(val_float)
        elif func_name == "tan":
            cos_val = math.cos(val_float)
            if abs(cos_val) < 1e-15:
                raise ValueError("Error: Tangent undefined at this angle")
            res = math.tan(val_float)

        if abs(res) < 1e-15:
            res = 0.0

        return Decimal(f"{res:.15g}")

    elif func_name in ("asin", "acos", "atan"):
        try:
            val_float = float(arg_val)
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
        if angle_unit == "degrees":
            pi = Decimal("3.141592653589793238462643383")
            res_dec = res_dec * Decimal("180") / pi

        final_float = float(res_dec)
        if abs(final_float) < 1e-15:
            final_float = 0.0
        return Decimal(f"{final_float:.15g}")

    raise ValueError(f"Error: Unknown function '{func_name}'")

def evaluate_postfix(postfix_tokens: list[str], initial_stack: list[Decimal] = None, angle_unit: str = "radians") -> list[Decimal]:
    """Evaluates a list of postfix tokens (RPN) on an initial stack

    using arbitrary-precision Decimal math.
    """
    if initial_stack is None:
        stack = []
    else:
        stack = list(initial_stack)
        
    constants = {
        "pi": Decimal("3.141592653589793238462643383"),
        "e": Decimal("2.718281828459045235360287471")
    }
    
    whitelisted_funcs = {
        "sin", "cos", "tan",
        "asin", "acos", "atan",
        "sqrt", "ln", "log", "log10"
    }
    
    with localcontext() as ctx:
        ctx.prec = 28
        
        for token in postfix_tokens:
            token_lower = token.lower()
            
            # 1. Constant
            if token_lower in constants:
                stack.append(constants[token_lower])
            # 2. Whitelisted function
            elif token_lower in whitelisted_funcs:
                if not stack:
                    raise RPNEvaluationError("Error: Stack underflow")
                val = stack.pop()
                res = _eval_func(token_lower, val, angle_unit)
                stack.append(res)
            # 3. Unary operator
            elif token in ('u+', 'u-'):
                if not stack:
                    raise RPNEvaluationError("Error: Stack underflow")
                val = stack.pop()
                if token == 'u-':
                    stack.append(-val)
                else:
                    stack.append(+val)
            # 4. Binary operator
            elif token in ('+', '-', '*', '/', '**', '^'):
                if len(stack) < 2:
                    raise RPNEvaluationError("Error: Stack underflow")
                right = stack.pop()
                left = stack.pop()
                res = _eval_binop(token, left, right)
                stack.append(res)
            # 5. Number operand
            else:
                # Disallow boolean keywords
                if token_lower in ('true', 'false'):
                    raise TypeError("Unsupported constant type")
                try:
                    # Parse number safely
                    stack.append(Decimal(token))
                except Exception:
                    raise ValueError(f"Error: Invalid operand or token: {token}")
                    
        # Normalize trailing zeros cleanly across all values on the stack
        normalized_stack = []
        for val in stack:
            try:
                if val == val.to_integral_value():
                    normalized_stack.append(val.to_integral_value())
                else:
                    normalized_stack.append(val.normalize())
            except Exception:
                normalized_stack.append(val)
                
        return normalized_stack
