import re
import math
from decimal import Decimal, InvalidOperation, Overflow

class ExpressionParser:
    """
    A high-precision Recursive Descent Parser for evaluating chained standard and
    scientific arithmetic expressions following PE(Unary)MDAS guidelines.
    """
    def __init__(self, expression: str, angle_unit: str = "radians"):
        self.expression = expression
        self.angle_unit = angle_unit.lower()
        self.tokens = self._tokenize(expression)
        self.pos = 0

    def _tokenize(self, expr: str) -> list[str]:
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

    def _peek(self) -> str | None:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _consume(self, expected: str | None = None) -> str:
        token = self._peek()
        if token is None:
            if expected:
                raise ValueError(f"Expected '{expected}' but reached end of expression")
            raise ValueError("Unexpected end of expression")
        if expected and token != expected:
            raise ValueError(f"Expected '{expected}' but found '{token}'")
        self.pos += 1
        return token

    def parse(self) -> Decimal:
        result = self._expr()
        if self.pos < len(self.tokens):
            raise ValueError(f"Unexpected token '{self.tokens[self.pos]}' at position {self.pos}")
        return result

    def _expr(self) -> Decimal:
        # expr -> term { ('+' | '-') term }
        val = self._term()
        while True:
            op = self._peek()
            if op in ('+', '-'):
                self._consume()
                right = self._term()
                if op == '+':
                    val = val + right
                else:
                    val = val - right
            else:
                break
        return val

    def _term(self) -> Decimal:
        # term -> unary { ('*' | '/') unary }
        val = self._unary()
        while True:
            op = self._peek()
            if op in ('*', '/'):
                self._consume()
                right = self._unary()
                if op == '*':
                    val = val * right
                else:
                    if right == Decimal('0'):
                        raise ZeroDivisionError("Division by zero")
                    val = val / right
            else:
                break
        return val

    def _unary(self) -> Decimal:
        # unary -> [ '+' | '-' ] power
        token = self._peek()
        is_negative = False
        
        if token == '-':
            is_negative = True
            self._consume()
        elif token == '+':
            self._consume()
            
        val = self._power()
        return -val if is_negative else val

    def _power(self) -> Decimal:
        # power -> primary [ '^' unary ]
        val = self._primary()
        if self._peek() == '^':
            self._consume('^')
            # Binary power operator is right-associative (or we can parse unary as exponent)
            exponent = self._unary()
            try:
                if exponent % 1 != 0:
                    if val < 0:
                        raise ValueError("Negative number raised to a fractional power is not allowed")
                    # Use float exponentiation for non-integer powers
                    res = float(val) ** float(exponent)
                    if math.isnan(res) or math.isinf(res):
                        raise ValueError("Result of exponentiation is undefined or too large")
                    val = Decimal(str(res))
                else:
                    # Decimal native power is highly precise for integers
                    val = val ** int(exponent)
            except (OverflowError, Overflow):
                raise ValueError("Result of exponentiation is too large (Overflow)")
            except (InvalidOperation, ValueError, ZeroDivisionError) as e:
                if "Negative number" in str(e):
                    raise e
                raise ValueError("Invalid power operation")
        return val

    def _primary(self) -> Decimal:
        # primary -> number | constant | function | '(' expr ')'
        token = self._peek()
        
        if token == '(':
            self._consume('(')
            val = self._expr()
            self._consume(')')
            return val
            
        # Check for Constants
        if token == 'pi':
            self._consume('pi')
            return Decimal('3.141592653589793238462643383')
        if token == 'e':
            self._consume('e')
            return Decimal('2.718281828459045235360287471')
            
        # Check for Functions
        if token in ('sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'ln', 'log', 'sqrt'):
            func_name = self._consume()
            self._consume('(')
            arg = self._expr()
            self._consume(')')
            return self._evaluate_function(func_name, arg)
            
        # Check for Numbers
        if token is not None and (token[0].isdigit() or token[0] == '.'):
            self._consume()
            try:
                return Decimal(token)
            except InvalidOperation:
                raise ValueError(f"Invalid numeric value '{token}'")
                
        raise ValueError(f"Expected number, constant, function, or '(' but found '{token or 'EOF'}'")

    def _evaluate_function(self, func_name: str, arg: Decimal) -> Decimal:
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
                if self.angle_unit == 'degrees':
                    val = math.radians(val)
                res = math.sin(val)
                if abs(res) < 1e-15:
                    res = 0.0
                return Decimal(str(res))
                
            elif func_name == 'cos':
                if self.angle_unit == 'degrees':
                    val = math.radians(val)
                res = math.cos(val)
                if abs(res) < 1e-15:
                    res = 0.0
                return Decimal(str(res))
                
            elif func_name == 'tan':
                if self.angle_unit == 'degrees':
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
                if self.angle_unit == 'degrees':
                    res = math.degrees(res)
                return Decimal(str(res))
                
            elif func_name == 'acos':
                if not (-1.0 <= val <= 1.0):
                    raise ValueError("acos input must be between -1 and 1")
                res = math.acos(val)
                if self.angle_unit == 'degrees':
                    res = math.degrees(res)
                return Decimal(str(res))
                
            elif func_name == 'atan':
                res = math.atan(val)
                if self.angle_unit == 'degrees':
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

def evaluate_expression(expression: str, angle_unit: str = "radians") -> Decimal:
    """
    Parses and evaluates the provided standard/scientific arithmetic expression with high precision.
    """
    parser = ExpressionParser(expression, angle_unit)
    return parser.parse()
