import re
import math
from decimal import Decimal, InvalidOperation, Overflow

def is_numeric(val: str) -> bool:
    try:
        Decimal(val)
        return True
    except InvalidOperation:
        return False

def tokenize_infix(expr: str) -> list[str]:
    if not expr.strip():
        raise ValueError("Expression is empty")
    
    # Match numbers (including decimals), words (functions/constants), operators (including ^), or whitespace
    pattern = re.compile(r'(\d*\.?\d+)|([a-zA-Z_][a-zA-Z0-9_]*)|([+\-*/()^])|(\s+)')
    tokens = []
    last_end = 0
    
    for match in pattern.finditer(expr):
        if match.start() != last_end:
            raise ValueError("Expression contains invalid characters")
        last_end = match.end()
        
        num, word, op, ws = match.groups()
        if num:
            tokens.append(num)
        elif word:
            tokens.append(word.lower())
        elif op:
            tokens.append(op)
        # Whitespace is ignored
        
    if last_end != len(expr):
        raise ValueError("Expression contains invalid characters")
        
    if not tokens:
        raise ValueError("Expression is empty")
        
    return tokens

def validate_infix_and_preprocess(tokens: list[str]) -> list[str]:
    preprocessed = []
    operators = {'+', '-', '*', '/', '^'}
    functions = {'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'ln', 'log', 'sqrt'}
    constants = {'pi', 'e'}
    
    n = len(tokens)
    for i, token in enumerate(tokens):
        next_tok = tokens[i+1] if i + 1 < n else None
        
        # Check if this and next token are numbers or constants
        is_num_or_const = token.isdigit() or (token.startswith('.') and len(token) > 1) or is_numeric(token) or token in constants
        next_is_num_or_const = next_tok and (next_tok.isdigit() or (next_tok.startswith('.') and len(next_tok) > 1) or is_numeric(next_tok) or next_tok in constants)
        
        if token in ('+', '-'):
            # Unary if first token or preceded by an operator or '('
            is_unary = (i == 0) or (tokens[i-1] in operators or tokens[i-1] == '(')
            if is_unary:
                preprocessed.append('u-' if token == '-' else 'u+')
                if not next_tok or (next_tok in operators and next_tok not in ('+', '-')) or next_tok == ')':
                    raise ValueError(f"Expected number, constant, function, or '(' but found '{next_tok or 'EOF'}'")
            else:
                preprocessed.append(token)
                if not next_tok or (next_tok in operators and next_tok not in ('+', '-')) or next_tok == ')':
                    raise ValueError(f"Expected number, constant, function, or '(' but found '{next_tok or 'EOF'}'")
        elif token in ('*', '/', '^'):
            preprocessed.append(token)
            if i == 0:
                raise ValueError(f"Expected number, constant, function, or '(' but found '{token}'")
            prev_tok = tokens[i-1]
            prev_is_operand = prev_tok.isdigit() or (prev_tok.startswith('.') and len(prev_tok) > 1) or is_numeric(prev_tok) or prev_tok in constants or prev_tok == ')'
            if not prev_is_operand:
                raise ValueError(f"Expected number, constant, function, or '(' but found '{token}'")
            if not next_tok or (next_tok in operators and next_tok not in ('+', '-')) or next_tok == ')':
                raise ValueError(f"Expected number, constant, function, or '(' but found '{next_tok or 'EOF'}'")
        elif token in functions:
            preprocessed.append(token)
            if next_tok != '(':
                raise ValueError(f"Expected '(' after function '{token}' but found '{next_tok or 'EOF'}'")
        elif token == '(':
            preprocessed.append(token)
            if next_tok in ('*', '/', '^') or next_tok == ')':
                raise ValueError(f"Expected number, constant, function, or '(' but found '{next_tok or 'EOF'}'")
        elif token == ')':
            preprocessed.append(token)
            if next_is_num_or_const or next_tok in functions or next_tok == '(':
                raise ValueError(f"Unexpected token '{next_tok}'")
        elif is_num_or_const:
            preprocessed.append(token)
            if next_is_num_or_const or next_tok in functions or next_tok == '(':
                raise ValueError(f"Unexpected token '{next_tok}'")
        else:
            raise ValueError(f"Expected number, constant, function, or '(' but found '{token}'")
            
    return preprocessed

def infix_to_postfix(tokens: list[str]) -> list[str]:
    # Validate and preprocess unary operators
    preprocessed = validate_infix_and_preprocess(tokens)
    
    output = []
    op_stack = []

    # Precedence definition (matching standard PEMDAS guidelines)
    precedence = {
        'sin': 6, 'cos': 6, 'tan': 6, 'asin': 6, 'acos': 6, 'atan': 6, 'ln': 6, 'log': 6, 'sqrt': 6,
        '^': 5,
        'u-': 4, 'u+': 4,
        '*': 3, '/': 3,
        '+': 2, '-': 2
    }
    
    associativity = {
        '^': 'right',
        'u-': 'right', 'u+': 'right',
        'sin': 'right', 'cos': 'right', 'tan': 'right', 'asin': 'right', 'acos': 'right', 'atan': 'right', 'ln': 'right', 'log': 'right', 'sqrt': 'right',
        '*': 'left', '/': 'left',
        '+': 'left', '-': 'left'
    }

    functions = {'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'ln', 'log', 'sqrt'}
    operators = {'+', '-', '*', '/', '^', 'u-', 'u+'}

    for token in preprocessed:
        if token.isdigit() or (token.startswith('.') and len(token) > 1) or is_numeric(token) or token in ('pi', 'e'):
            output.append(token)
        elif token in functions:
            op_stack.append(token)
        elif token in operators:
            op_prec = precedence[token]
            op_assoc = associativity[token]
            while op_stack:
                top = op_stack[-1]
                if top == '(':
                    break
                
                top_prec = precedence.get(top, 0)
                # Functions always have high precedence and are popped
                if (top in functions) or (top_prec > op_prec) or (top_prec == op_prec and op_assoc == 'left'):
                    output.append(op_stack.pop())
                else:
                    break
            op_stack.append(token)
        elif token == '(':
            op_stack.append(token)
        elif token == ')':
            matched = False
            while op_stack:
                top = op_stack[-1]
                if top == '(':
                    op_stack.pop()
                    matched = True
                    break
                output.append(op_stack.pop())
            if not matched:
                raise ValueError("Unexpected token ')'")
        else:
            raise ValueError(f"Unknown token '{token}'")

    while op_stack:
        top = op_stack.pop()
        if top in ('(', ')'):
            raise ValueError("Expected ')' but reached end of expression")
        output.append(top)

    return output

def evaluate_postfix(tokens: list[str], angle_unit: str = "radians") -> Decimal:
    stack = []
    
    constants = {
        'pi': Decimal('3.141592653589793238462643383'),
        'e': Decimal('2.718281828459045235360287471')
    }

    functions = {'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'ln', 'log', 'sqrt'}
    binary_operators = {'+', '-', '*', '/', '^'}
    unary_operators = {'u-', 'u+'}

    for token in tokens:
        if token in constants:
            stack.append(constants[token])
        elif token in unary_operators:
            if not stack:
                raise ValueError(f"Insufficient operands on the stack for operator '{token}'")
            arg = stack.pop()
            if token == 'u-':
                stack.append(-arg)
            else:
                stack.append(arg)
        elif token in functions:
            if not stack:
                raise ValueError(f"Insufficient operands on the stack for function '{token}'")
            arg = stack.pop()
            res = evaluate_function_impl(token, arg, angle_unit)
            stack.append(res)
        elif token in binary_operators:
            if len(stack) < 2:
                raise ValueError(f"Insufficient operands on the stack for operator '{token}'")
            right = stack.pop()
            left = stack.pop()
            res = evaluate_binary_impl(left, token, right)
            stack.append(res)
        else:
            # Must be a number
            try:
                stack.append(Decimal(token))
            except InvalidOperation:
                raise ValueError(f"Expected number, constant, function, or operator but found '{token}'")
                
    if len(stack) != 1:
        if len(stack) == 0:
            raise ValueError("Expression is empty or evaluation resulted in empty stack")
        raise ValueError(f"Unexpected values on stack. Unresolved tokens remain: {len(stack)} items")

    return stack[0]

def evaluate_function_impl(func_name: str, arg: Decimal, angle_unit: str) -> Decimal:
    val = float(arg)
    
    try:
        if func_name == 'sqrt':
            if arg < 0:
                raise ValueError("Square root of negative number is not allowed")
            return arg.sqrt()
        
        elif func_name == 'ln':
            if arg <= 0:
                raise ValueError("Logarithm of non-positive number is not allowed")
            return arg.ln()
        
        elif func_name == 'log':
            if arg <= 0:
                raise ValueError("Logarithm of non-positive number is not allowed")
            return arg.log10()
        
        elif func_name == 'sin':
            if angle_unit == 'degrees':
                val = math.radians(val)
            res = math.sin(val)
            if abs(res) < 1e-15:
                res = 0.0
            return Decimal(str(res))
            
        elif func_name == 'cos':
            if angle_unit == 'degrees':
                val = math.radians(val)
            res = math.cos(val)
            if abs(res) < 1e-15:
                res = 0.0
            return Decimal(str(res))
            
        elif func_name == 'tan':
            if angle_unit == 'degrees':
                if abs((val - 90) % 180) < 1e-9:
                    raise ZeroDivisionError("Tangent is undefined for this angle")
                val = math.radians(val)
            else:
                if abs((val - math.pi / 2) % math.pi) < 1e-9:
                    raise ZeroDivisionError("Tangent is undefined for this angle")
            res = math.tan(val)
            if abs(res) < 1e-15:
                res = 0.0
            return Decimal(str(res))
            
        elif func_name == 'asin':
            if not (-1.0 <= val <= 1.0):
                raise ValueError("asin input must be between -1 and 1")
            res = math.asin(val)
            if angle_unit == 'degrees':
                res = math.degrees(res)
            return Decimal(str(res))
            
        elif func_name == 'acos':
            if not (-1.0 <= val <= 1.0):
                raise ValueError("acos input must be between -1 and 1")
            res = math.acos(val)
            if angle_unit == 'degrees':
                res = math.degrees(res)
            return Decimal(str(res))
            
        elif func_name == 'atan':
            res = math.atan(val)
            if angle_unit == 'degrees':
                res = math.degrees(res)
            return Decimal(str(res))
            
        else:
            raise ValueError(f"Unknown function '{func_name}'")
            
    except ZeroDivisionError as e:
        raise e
    except ValueError as e:
        raise e
    except Exception as e:
        raise ValueError(f"Math error in {func_name}: {str(e)}")

def evaluate_binary_impl(left: Decimal, op: str, right: Decimal) -> Decimal:
    if op == '+':
        return left + right
    elif op == '-':
        return left - right
    elif op == '*':
        return left * right
    elif op == '/':
        if right == Decimal('0'):
            raise ZeroDivisionError("Division by zero")
        return left / right
    elif op == '^':
        try:
            if right % 1 != 0:
                if left < 0:
                    raise ValueError("Negative number raised to a fractional power is not allowed")
                res = float(left) ** float(right)
                if math.isnan(res) or math.isinf(res):
                    raise ValueError("Result of exponentiation is undefined or too large")
                return Decimal(str(res))
            else:
                return left ** int(right)
        except (OverflowError, Overflow):
            raise ValueError("Result of exponentiation is too large (Overflow)")
        except (InvalidOperation, ValueError, ZeroDivisionError) as e:
            if "Negative number" in str(e):
                raise e
            raise ValueError("Invalid power operation")
    else:
        raise ValueError(f"Unknown operator '{op}'")

def evaluate_expression(expression: str, angle_unit: str = "radians", mode: str = "infix") -> Decimal:
    """
    Parses and evaluates the provided standard (infix) or postfix (RPN) expression with high precision.
    """
    angle_unit = angle_unit.lower()
    mode = mode.lower()
    
    if mode == "postfix":
        if not expression.strip():
            raise ValueError("Expression is empty")
        tokens = expression.strip().split()
        return evaluate_postfix(tokens, angle_unit)
    
    elif mode == "infix":
        tokens = tokenize_infix(expression)
        postfix_tokens = infix_to_postfix(tokens)
        return evaluate_postfix(postfix_tokens, angle_unit)
        
    else:
        raise ValueError(f"Invalid mode '{mode}'. Must be 'infix' or 'postfix'")
