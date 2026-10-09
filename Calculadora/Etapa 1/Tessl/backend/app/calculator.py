import re
from decimal import Decimal, InvalidOperation

class ExpressionParser:
    """
    A high-precision Recursive Descent Parser for evaluating chained arithmetic
    expressions following PEMDAS guidelines.
    """
    def __init__(self, expression: str):
        self.expression = expression
        self.tokens = self._tokenize(expression)
        self.pos = 0

    def _tokenize(self, expr: str) -> list[str]:
        if not expr.strip():
            raise ValueError("Expression is empty")
        
        # Match numbers (including decimals), operators, or whitespace
        pattern = re.compile(r'(\d*\.?\d+)|([+\-*/()])|(\s+)')
        tokens = []
        last_end = 0
        
        for match in pattern.finditer(expr):
            # Check for unmatched characters (invalid tokens)
            if match.start() != last_end:
                raise ValueError("Expression contains invalid characters")
            last_end = match.end()
            
            num, op, ws = match.groups()
            if num:
                tokens.append(num)
            elif op:
                tokens.append(op)
            # Whitespace is ignored and not added to tokens
            
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
        # term -> factor { ('*' | '/') factor }
        val = self._factor()
        while True:
            op = self._peek()
            if op in ('*', '/'):
                self._consume()
                right = self._factor()
                if op == '*':
                    val = val * right
                else:
                    if right == Decimal('0'):
                        raise ZeroDivisionError("Division by zero")
                    val = val / right
            else:
                break
        return val

    def _factor(self) -> Decimal:
        # factor -> [ '+' | '-' ] ( number | '(' expr ')' )
        token = self._peek()
        is_negative = False
        
        if token == '-':
            is_negative = True
            self._consume()
        elif token == '+':
            self._consume()
        
        token = self._peek()
        if token == '(':
            self._consume('(')
            val = self._expr()
            self._consume(')')
        elif token is not None and (token[0].isdigit() or token[0] == '.'):
            self._consume()
            try:
                val = Decimal(token)
            except InvalidOperation:
                raise ValueError(f"Invalid numeric value '{token}'")
        else:
            raise ValueError(f"Expected number or '(' but found '{token or 'EOF'}'")
        
        return -val if is_negative else val

def evaluate_expression(expression: str) -> Decimal:
    """
    Parses and evaluates the provided arithmetic expression with high precision.
    """
    parser = ExpressionParser(expression)
    return parser.parse()
