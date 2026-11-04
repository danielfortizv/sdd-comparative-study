import math
import re
from decimal import Decimal, InvalidOperation
from src.api.v1.errors import CalculatorError

# Precedence and associativity for infix operators
PRECEDENCE = {
    "u+": 4, "u-": 4,  # Unary positive/negation
    "**": 3,           # Exponentiation
    "*": 2, "/": 2,    # Multiplication/Division
    "+": 1, "-": 1     # Addition/Subtraction
}

# True for right-associative, False for left-associative
RIGHT_ASSOC = {
    "u+": True, "u-": True,
    "**": True
}

# Scientific functions and mathematical constants
FUNCTIONS = {"sin", "cos", "tan", "asin", "acos", "atan", "sqrt", "ln", "log10", "root"}
CONSTANTS = {"pi", "e"}

def is_number(s: str) -> bool:
    """Helper to check if a token string can be parsed as a high-precision Decimal."""
    try:
        Decimal(s)
        return True
    except (InvalidOperation, ValueError, TypeError):
        return False

def format_decimal(d: Decimal) -> str:
    """Formats a Decimal to a user-friendly standard representation, avoiding scientific notation for clean numbers."""
    try:
        if d == d.to_integral_value():
            return str(d.to_integral_value())
    except Exception:
        pass
    s = str(d.normalize())
    if "E" in s or "e" in s:
        # Use high-precision float formatting to strip scientific exponent representation
        return f"{float(d):.14g}"
    return s

def tokenize(expression: str) -> list[str]:
    """Tokenizes an infix expression into individual symbols, operators, numbers, and functions."""
    cleaned = "".join(expression.split())  # Remove whitespaces for safe infix tokenization
    # Translate caret ^ to standard ** exponent symbol
    cleaned = cleaned.replace("^", "**")
    
    # Tokenizer matches floating decimals, integer numbers, double carets **, individual symbols, parentheses, commas, or words
    token_pattern = re.compile(r'(\d+\.\d+|\d+|\*\*|[+\-*/(),]|\w+)')
    tokens = []
    
    for m in token_pattern.finditer(cleaned):
        tokens.append(m.group(1))
        
    # Verify that the parsed tokens perfectly reconstruct the input string to prevent invalid characters
    if "".join(tokens) != cleaned:
        raise CalculatorError("SYNTAX_ERROR", "The expression contains invalid mathematical characters.")
        
    return tokens

def process_unary_operators(tokens: list[str]) -> list[str]:
    """Identifies and translates unary '+' and '-' operators to unique 'u+' and 'u-' tokens, validating binary operator sequences."""
    processed = []
    binary_ops = {"*", "/", "**"}
    
    for i, token in enumerate(tokens):
        if token in ("+", "-"):
            # A plus or minus is unary if it is at the start of the token stream, or immediately follows another operator or symbol
            is_unary = False
            if i == 0:
                is_unary = True
            else:
                prev = tokens[i - 1]
                if prev in ("+", "-", "*", "/", "**", "(", ","):
                    is_unary = True
            
            if is_unary:
                processed.append("u" + token)
            else:
                # It is a binary operator. Let's make sure it doesn't follow another operator, parenthesis, or comma
                if i > 0:
                    prev = tokens[i - 1]
                    if prev in ("+", "-", "*", "/", "**", "(", ","):
                        raise CalculatorError("SYNTAX_ERROR", f"Syntax error: binary operator '{token}' cannot follow '{prev}'.")
                processed.append(token)
                
        elif token in binary_ops:
            # A binary operator cannot be at the very start of the expression
            if i == 0:
                raise CalculatorError("SYNTAX_ERROR", f"Syntax error: expression cannot start with binary operator '{token}'.")
            prev = tokens[i - 1]
            # A binary operator cannot follow another operator, parenthesis, or comma
            if prev in ("+", "-", "*", "/", "**", "(", ","):
                raise CalculatorError("SYNTAX_ERROR", f"Syntax error: binary operator '{token}' cannot follow '{prev}'.")
            processed.append(token)
            
        else:
            processed.append(token)
            
    return processed

def infix_to_postfix(tokens: list[str]) -> list[str]:
    """Converts a tokenized infix expression into a postfix (RPN) sequence via the Shunting Yard Algorithm."""
    output_queue = []
    operator_stack = []
    
    for token in tokens:
        if is_number(token) or token in CONSTANTS:
            output_queue.append(token)
            
        elif token in FUNCTIONS:
            operator_stack.append(token)
            
        elif token == ",":
            found_paren = False
            while operator_stack:
                if operator_stack[-1] == "(":
                    found_paren = True
                    break
                output_queue.append(operator_stack.pop())
            if not found_paren:
                raise CalculatorError("SYNTAX_ERROR", "Comma or open parenthesis mismatch.")
                
        elif token in PRECEDENCE:
            o1 = token
            while operator_stack:
                o2 = operator_stack[-1]
                if o2 in PRECEDENCE:
                    p1 = PRECEDENCE[o1]
                    p2 = PRECEDENCE[o2]
                    # Pop o2 if o1 is left-associative and has equal or lower precedence, or right-associative and lower precedence
                    if (not RIGHT_ASSOC.get(o1, False) and p1 <= p2) or (RIGHT_ASSOC.get(o1, False) and p1 < p2):
                        output_queue.append(operator_stack.pop())
                    else:
                        break
                else:
                    break
            operator_stack.append(o1)
            
        elif token == "(":
            operator_stack.append(token)
            
        elif token == ")":
            found_paren = False
            while operator_stack:
                if operator_stack[-1] == "(":
                    found_paren = True
                    operator_stack.pop()  # Pop the left parenthesis
                    break
                output_queue.append(operator_stack.pop())
            if not found_paren:
                raise CalculatorError("SYNTAX_ERROR", "Mismatched parentheses: unclosed open parenthesis or missing matching open parenthesis.")
            
            if operator_stack and operator_stack[-1] in FUNCTIONS:
                output_queue.append(operator_stack.pop())
                
        else:
            raise CalculatorError("SYNTAX_ERROR", f"Unknown mathematical token: {token}")
            
    while operator_stack:
        op = operator_stack.pop()
        if op == "(":
            raise CalculatorError("SYNTAX_ERROR", "Mismatched parentheses: unclosed open parenthesis.")
        output_queue.append(op)
        
    return output_queue

def evaluate_postfix(postfix_tokens: list[str], angle_unit: str = "radians") -> list[Decimal]:
    """Evaluates a list of postfix (RPN) tokens using a stack and returns the final execution stack state."""
    stack = []
    
    for token in postfix_tokens:
        if is_number(token):
            stack.append(Decimal(token))
            
        elif token == "pi":
            stack.append(Decimal(f"{math.pi:.28g}").normalize())
            
        elif token == "e":
            stack.append(Decimal(f"{math.e:.28g}").normalize())
            
        elif token == "u-":
            if len(stack) < 1:
                raise CalculatorError("STACK_UNDERFLOW", "Unary negation expects 1 operand.")
            x = stack.pop()
            stack.append(-x)
            
        elif token == "u+":
            if len(stack) < 1:
                raise CalculatorError("STACK_UNDERFLOW", "Unary positive expects 1 operand.")
            # Unary positive is a no-op
            
        elif token in ("+", "-", "*", "/", "**"):
            if len(stack) < 2:
                raise CalculatorError("STACK_UNDERFLOW", f"Binary operator '{token}' expects 2 operands.")
            right = stack.pop()
            left = stack.pop()
            
            try:
                if token == "+":
                    res = left + right
                elif token == "-":
                    res = left - right
                elif token == "*":
                    res = left * right
                elif token == "/":
                    if right == Decimal("0"):
                        raise CalculatorError("DIVISION_BY_ZERO", "Cannot divide a decimal number by exactly zero.")
                    res = left / right
                elif token == "**":
                    if left < 0 and right % 1 != 0:
                        raise CalculatorError("DOMAIN_ERROR", "Fractional power of a negative number is undefined.")
                    res = left ** right
                
                stack.append(res)
            except CalculatorError:
                raise
            except OverflowError:
                raise CalculatorError("OVERFLOW", f"The math calculation resulted in arithmetic overflow during '{token}' operator.")
            except Exception as e:
                raise CalculatorError("DOMAIN_ERROR", f"Invalid operation: {str(e)}")
                
        elif token in FUNCTIONS:
            if token == "root":
                if len(stack) < 2:
                    raise CalculatorError("STACK_UNDERFLOW", "Function 'root(radicand, degree)' expects 2 operands on the stack.")
                y = stack.pop()  # degree
                x = stack.pop()  # radicand
                
                if y == Decimal("0"):
                    raise CalculatorError("DIVISION_BY_ZERO", "Root degree cannot be zero.")
                if x < 0:
                    if y % 1 != 0:
                        raise CalculatorError("DOMAIN_ERROR", "Fractional root of a negative number is undefined.")
                    if int(y) % 2 == 0:
                        raise CalculatorError("DOMAIN_ERROR", "Even root of a negative number is undefined.")
                
                try:
                    # Leverage floating-point for fractional root calculations and normalize back to Decimal
                    res_val = float(x) ** (1.0 / float(y))
                    res = Decimal(f"{res_val:.28g}").normalize()
                    stack.append(res)
                except OverflowError:
                    raise CalculatorError("OVERFLOW", "The root operation resulted in an arithmetic overflow.")
                except Exception as e:
                    raise CalculatorError("DOMAIN_ERROR", f"Domain error in root function: {str(e)}")
                    
            else:
                # Unary mathematical functions
                if len(stack) < 1:
                    raise CalculatorError("STACK_UNDERFLOW", f"Function '{token}' expects 1 operand on the stack.")
                x_dec = stack.pop()
                x = float(x_dec)
                
                try:
                    if token == "sin":
                        val = x
                        if angle_unit == "degrees":
                            val = math.radians(val)
                        res_val = math.sin(val)
                    elif token == "cos":
                        val = x
                        if angle_unit == "degrees":
                            val = math.radians(val)
                        res_val = math.cos(val)
                    elif token == "tan":
                        val = x
                        if angle_unit == "degrees":
                            if abs(val % 180 - 90) < 1e-9:
                                raise CalculatorError("DOMAIN_ERROR", "Tangent is undefined at 90 degrees or odd multiples.")
                            val_rad = math.radians(val)
                            res_val = math.tan(val_rad)
                        else:
                            if abs(math.cos(val)) < 1e-15:
                                raise CalculatorError("DOMAIN_ERROR", "Tangent is undefined at odd multiples of pi/2.")
                            res_val = math.tan(val)
                    elif token == "asin":
                        if x < -1.0 or x > 1.0:
                            raise CalculatorError("DOMAIN_ERROR", "Inverse trigonometric input must be between -1 and 1.")
                        res_val = math.asin(x)
                        if angle_unit == "degrees":
                            res_val = math.degrees(res_val)
                    elif token == "acos":
                        if x < -1.0 or x > 1.0:
                            raise CalculatorError("DOMAIN_ERROR", "Inverse trigonometric input must be between -1 and 1.")
                        res_val = math.acos(x)
                        if angle_unit == "degrees":
                            res_val = math.degrees(res_val)
                    elif token == "atan":
                        res_val = math.atan(x)
                        if angle_unit == "degrees":
                            res_val = math.degrees(res_val)
                    elif token == "sqrt":
                        if x < 0:
                            raise CalculatorError("DOMAIN_ERROR", "Cannot take the square root of a negative number.")
                        res_val = math.sqrt(x)
                    elif token == "ln":
                        if x <= 0:
                            raise CalculatorError("DOMAIN_ERROR", "Logarithm input must be strictly positive.")
                        res_val = math.log(x)
                    elif token == "log10":
                        if x <= 0:
                            raise CalculatorError("DOMAIN_ERROR", "Logarithm input must be strictly positive.")
                        res_val = math.log10(x)
                        
                    res = Decimal(f"{res_val:.28g}").normalize()
                    stack.append(res)
                except CalculatorError:
                    raise
                except OverflowError:
                    raise CalculatorError("OVERFLOW", f"Function '{token}' resulted in arithmetic overflow.")
                except Exception as e:
                    raise CalculatorError("DOMAIN_ERROR", f"Domain error in function '{token}': {str(e)}")
                    
        else:
            raise CalculatorError("SYNTAX_ERROR", f"Invalid token inside postfix expression: {token}")
            
    return stack

def evaluate_expression_full(expression: str, angle_unit: str = "radians", mode: str = "standard") -> tuple[Decimal, list[str]]:
    """Evaluates a mathematical expression and returns both the final computed decimal result and the remaining stack."""
    cleaned = expression.strip()
    if not cleaned:
        raise CalculatorError("SYNTAX_ERROR", "The mathematical expression cannot be empty.")
        
    if mode == "rpn":
        # Process a space-separated string of postfix (RPN) tokens directly
        tokens = cleaned.split()
        final_stack = evaluate_postfix(tokens, angle_unit=angle_unit)
        if not final_stack:
            raise CalculatorError("SYNTAX_ERROR", "Evaluation stack is empty.")
        result = final_stack[-1]
        stack_str_list = [format_decimal(item) for item in final_stack]
        return result, stack_str_list
        
    else:
        # Standard Infix mode: tokenize -> unary process -> Shunting Yard -> evaluate
        tokens = tokenize(cleaned)
        processed_tokens = process_unary_operators(tokens)
        postfix_tokens = infix_to_postfix(processed_tokens)
        final_stack = evaluate_postfix(postfix_tokens, angle_unit=angle_unit)
        if not final_stack:
            raise CalculatorError("SYNTAX_ERROR", "Evaluation stack is empty.")
        if len(final_stack) > 1:
            raise CalculatorError("SYNTAX_ERROR", "Standard expression evaluation resulted in multiple values on the stack (missing operator).")
        result = final_stack[0]
        return result, [format_decimal(result)]

def evaluate_expression(expression: str, angle_unit: str = "radians") -> Decimal:
    """Safely evaluates a scientific math expression in standard infix mode (backward compatibility wrapper)."""
    result, _ = evaluate_expression_full(expression, angle_unit=angle_unit, mode="standard")
    return result
