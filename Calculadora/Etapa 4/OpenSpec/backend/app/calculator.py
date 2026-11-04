import decimal
import math

# Configure Decimal precision and behavior
decimal.getcontext().prec = 28

# Set up physical math constants
PI = decimal.Decimal("3.1415926535897932384626433832795")
E_CONST = decimal.Decimal("2.7182818284590452353602874713527")

class CalculatorError(ValueError):
    pass

PRECEDENCE = {
    "u-": 5,
    "u+": 5,
    "**": 4,
    "*": 2,
    "/": 2,
    "+": 1,
    "-": 1,
}

RIGHT_ASSOCIATIVE = {"**", "u-", "u+"}

FUNCTIONS = {"sin", "cos", "tan", "asin", "acos", "atan", "ln", "log10", "sqrt", "root"}

def tokenize(expr: str) -> list[str]:
    """
    Scans the mathematical expression string and breaks it down into individual tokens.
    """
    tokens = []
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
            continue
            
        # Number token
        if c.isdigit() or c == '.':
            val = ""
            has_dot = False
            while i < n and (expr[i].isdigit() or expr[i] == '.'):
                if expr[i] == '.':
                    if has_dot:
                        raise CalculatorError("Malformed expression or mismatched parentheses")
                    has_dot = True
                val += expr[i]
                i += 1
            tokens.append(val)
            
        # Alphabetical names (functions and constants)
        elif c.isalpha():
            name = ""
            while i < n and expr[i].isalnum():
                name += expr[i]
                i += 1
            tokens.append(name)
            
        # Power operator **
        elif c == '*' and i + 1 < n and expr[i+1] == '*':
            tokens.append("**")
            i += 2
            
        # Single-character tokens
        elif c in "+-*/(),":
            tokens.append(c)
            i += 1
        else:
            raise CalculatorError("Invalid characters in expression")
    return tokens

def validate_function_args(tokens: list[str]):
    """
    Validates that function argument counts (e.g., sqrt(), root(x, y)) match expectations before processing.
    """
    i = 0
    n = len(tokens)
    while i < n:
        if tokens[i] in FUNCTIONS:
            func_name = tokens[i]
            if i + 1 < n and tokens[i+1] == "(":
                depth = 1
                j = i + 2
                comma_count = 0
                has_elements = False
                while j < n and depth > 0:
                    if tokens[j] == "(":
                        depth += 1
                    elif tokens[j] == ")":
                        depth -= 1
                    elif tokens[j] == ",":
                        if depth == 1:
                            comma_count += 1
                    else:
                        if depth == 1:
                            has_elements = True
                    j += 1
                
                if depth > 0:
                    raise CalculatorError("Malformed expression or mismatched parentheses")
                    
                if not has_elements and comma_count == 0:
                    arg_count = 0
                else:
                    arg_count = comma_count + 1
                    
                if func_name == "root":
                    if arg_count != 2:
                        raise CalculatorError("root() requires exactly 2 arguments (base, degree)")
                else:
                    if arg_count != 1:
                        raise CalculatorError(f"{func_name}() requires exactly 1 argument")
        i += 1

def preprocess_tokens(tokens: list[str]) -> list[str]:
    """
    Identifies and tags unary operators (u- and u+) in the infix token list.
    """
    processed = []
    operators_and_delimiters = {"+", "-", "*", "/", "**", "(", ","}
    for idx, token in enumerate(tokens):
        if token == "-" or token == "+":
            is_unary = False
            if idx == 0:
                is_unary = True
            else:
                prev = tokens[idx - 1]
                if prev in operators_and_delimiters:
                    is_unary = True
            if is_unary:
                processed.append("u-" if token == "-" else "u+")
            else:
                processed.append(token)
        else:
            processed.append(token)
    return processed

def infix_to_postfix(tokens: list[str]) -> list[str]:
    """
    Converts an infix token list to postfix (RPN) notation using the Shunting Yard Algorithm.
    """
    output = []
    op_stack = []
    for token in tokens:
        # Check for legacy and undefined variable keywords
        if token == "not" or token == "Not":
            raise CalculatorError("Unsupported unary operator: Not")
        elif token.isalpha() and token not in FUNCTIONS and token not in {"pi", "e"}:
            raise CalculatorError(f"Undefined variable: {token}")

        # Check if number (by attempting conversion) or is constant
        is_num = False
        try:
            decimal.Decimal(token)
            is_num = True
        except (decimal.InvalidOperation, ValueError, TypeError):
            pass

        if is_num or token == "pi" or token == "e":
            output.append(token)
        elif token in FUNCTIONS:
            op_stack.append(token)
        elif token == ",":
            while op_stack and op_stack[-1] != "(":
                output.append(op_stack.pop())
            if not op_stack:
                raise CalculatorError("Malformed expression or mismatched parentheses")
        elif token in PRECEDENCE:
            while op_stack and op_stack[-1] in PRECEDENCE:
                top_op = op_stack[-1]
                if (PRECEDENCE[top_op] > PRECEDENCE[token]) or \
                   (PRECEDENCE[top_op] == PRECEDENCE[token] and token not in RIGHT_ASSOCIATIVE):
                    output.append(op_stack.pop())
                else:
                    break
            op_stack.append(token)
        elif token == "(":
            op_stack.append(token)
        elif token == ")":
            while op_stack and op_stack[-1] != "(":
                output.append(op_stack.pop())
            if not op_stack:
                raise CalculatorError("Malformed expression or mismatched parentheses")
            op_stack.pop() # pop '('
            if op_stack and op_stack[-1] in FUNCTIONS:
                output.append(op_stack.pop())
        else:
            raise CalculatorError(f"Invalid token: {token}")
            
    while op_stack:
        top_op = op_stack.pop()
        if top_op == "(" or top_op == ")":
            raise CalculatorError("Malformed expression or mismatched parentheses")
        output.append(top_op)
        
    return output

def evaluate_postfix(postfix_tokens: list[str], angle_unit: str = "radians", initial_stack: list[decimal.Decimal] = None) -> list[decimal.Decimal]:
    """
    Evaluates a postfix (RPN) token stream via a stack execution engine.
    """
    stack = []
    if initial_stack is not None:
        stack = list(initial_stack)
        
    for token in postfix_tokens:
        # Attempt number conversion
        is_num = False
        try:
            val = decimal.Decimal(token)
            stack.append(val)
            is_num = True
            continue
        except (decimal.InvalidOperation, ValueError, TypeError):
            pass
            
        if token == "pi":
            stack.append(PI)
        elif token == "e":
            stack.append(E_CONST)
        elif token == "u-":
            if not stack:
                raise CalculatorError("Insufficient operands on stack")
            x = stack.pop()
            stack.append(-x)
        elif token == "u+":
            if not stack:
                raise CalculatorError("Insufficient operands on stack")
            x = stack.pop()
            stack.append(+x)
        elif token in FUNCTIONS:
            if token == "root":
                if len(stack) < 2:
                    raise CalculatorError("Insufficient operands on stack")
                degree = stack.pop()
                base = stack.pop()
                if degree == decimal.Decimal('0'):
                    raise CalculatorError("Division by zero")
                try:
                    exponent = decimal.Decimal("1") / degree
                    if base < decimal.Decimal('0') and (degree % decimal.Decimal('2') == decimal.Decimal('0')):
                        raise CalculatorError("Math domain error")
                    res = base ** exponent
                    stack.append(res)
                except (decimal.InvalidOperation, ArithmeticError, ValueError, TypeError):
                    raise CalculatorError("Math domain error")
            else:
                if not stack:
                    raise CalculatorError("Insufficient operands on stack")
                x = stack.pop()
                if token == "sqrt":
                    if x < decimal.Decimal('0'):
                        raise CalculatorError("Math domain error")
                    stack.append(x.sqrt())
                elif token == "ln":
                    if x <= decimal.Decimal('0'):
                        raise CalculatorError("Math domain error")
                    stack.append(x.ln())
                elif token == "log10":
                    if x <= decimal.Decimal('0'):
                        raise CalculatorError("Math domain error")
                    stack.append(x.log10())
                elif token in {"sin", "cos", "tan", "asin", "acos", "atan"}:
                    try:
                        f_val = float(x)
                        if token in {"sin", "cos", "tan"}:
                            r = math.radians(f_val) if angle_unit == "degrees" else f_val
                            if token == "sin":
                                res = math.sin(r)
                            elif token == "cos":
                                res = math.cos(r)
                            elif token == "tan":
                                if abs(math.cos(r)) < 1e-15:
                                    raise CalculatorError("Math domain error")
                                res = math.tan(r)
                        else:  # Inverse trig
                            if token in {"asin", "acos"} and abs(f_val) > 1.0:
                                raise CalculatorError("Math domain error")
                            if token == "asin":
                                res = math.asin(f_val)
                            elif token == "acos":
                                res = math.acos(f_val)
                            elif token == "atan":
                                res = math.atan(f_val)
                            if angle_unit == "degrees":
                                res = math.degrees(res)
                                
                        rounded_res = round(res, 15)
                        stack.append(decimal.Decimal(str(rounded_res)))
                    except CalculatorError:
                        raise
                    except (decimal.InvalidOperation, ArithmeticError, ValueError, TypeError):
                        raise CalculatorError("Math domain error")
        elif token in PRECEDENCE:
            # Binary operator
            if len(stack) < 2:
                raise CalculatorError("Insufficient operands on stack")
            right = stack.pop()
            left = stack.pop()
            
            try:
                if token == "+":
                    stack.append(left + right)
                elif token == "-":
                    stack.append(left - right)
                elif token == "*":
                    stack.append(left * right)
                elif token == "/":
                    if right == decimal.Decimal('0'):
                        raise CalculatorError("Division by zero")
                    stack.append(left / right)
                elif token == "**":
                    if left == decimal.Decimal('0') and right < decimal.Decimal('0'):
                        raise CalculatorError("Division by zero")
                    stack.append(left ** right)
            except CalculatorError:
                raise
            except decimal.DivisionByZero:
                raise CalculatorError("Division by zero")
            except (decimal.InvalidOperation, ArithmeticError, ValueError, TypeError):
                raise CalculatorError("Math domain error")
        else:
            raise CalculatorError(f"Invalid token: {token}")
            
    return stack

def evaluate_expression(expr: str, angle_unit: str = "radians") -> decimal.Decimal:
    """
    Evaluates a standard infix mathematical expression.
    """
    expr = expr.strip()
    if not expr:
        raise CalculatorError("Expression cannot be empty")
        
    # Strictly validate allowed characters
    allowed_chars = set("0123456789.+-*/(), abcdefghijklmnopqrstuvwxyz")
    if not all(c in allowed_chars for c in expr):
        raise CalculatorError("Invalid characters in expression")
        
    try:
        tokens = tokenize(expr)
        validate_function_args(tokens)
        preprocessed = preprocess_tokens(tokens)
        postfix = infix_to_postfix(preprocessed)
        final_stack = evaluate_postfix(postfix, angle_unit)
    except CalculatorError as e:
        if str(e) == "Insufficient operands on stack":
            raise CalculatorError("Malformed expression or mismatched parentheses")
        raise
        
    if len(final_stack) != 1:
        raise CalculatorError("Malformed expression or mismatched parentheses")
        
    return final_stack[0].normalize()
