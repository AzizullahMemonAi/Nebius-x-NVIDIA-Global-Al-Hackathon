"""A small calculator with explicit errors for invalid input."""


class CalculatorError(ValueError):
    """Raised when an expression or operation is invalid."""


class Calculator:
    def __init__(self):
        self.history = []

    def add(self, a, b):
        return self._record("add", a + b, a, b)

    def sub(self, a, b):
        return self._record("sub", a - b, a, b)

    def mul(self, a, b):
        return self._record("mul", a * b, a, b)

    def div(self, a, b):
        if b == 0:
            raise CalculatorError("division by zero")
        return self._record("div", a / b, a, b)

    def _record(self, operation, result, a, b):
        self.history.append(
            {"op": operation, "a": a, "b": b, "result": result}
        )
        return result


def parse_expression(raw):
    """Evaluate a simple expression such as ``"2 * 3"``."""
    tokens = (raw or "").split()
    if len(tokens) != 3:
        raise CalculatorError("enter two numbers and an operator")

    left, operator, right = tokens
    try:
        a, b = float(left), float(right)
    except ValueError as exc:
        raise CalculatorError("operands must be numbers") from exc

    calculator = Calculator()
    operations = {
        "+": calculator.add,
        "-": calculator.sub,
        "*": calculator.mul,
        "/": calculator.div,
    }
    try:
        operation = operations[operator]
    except KeyError as exc:
        raise CalculatorError(f"unsupported operator: {operator}") from exc
    return operation(a, b)
