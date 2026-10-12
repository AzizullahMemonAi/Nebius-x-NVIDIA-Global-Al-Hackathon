"""Minimal calculator used by the Nexora demo workspace.

Contains a known bug: empty input raises ZeroDivisionError instead of
returning a well-defined result.
"""


class CalculatorError(Exception):
    """Raised for unsupported operations or invalid input."""


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
        # BUG: b == 0 (and the empty-input case that produces it) is not
        # guarded, so callers receive a ZeroDivisionError.
        return self._record("div", a / b, a, b)

    def safe_div(self, a, b):
        if b == 0:
            raise CalculatorError("division by zero")
        return a / b

    def _record(self, op, result, a, b):
        self.history.append({"op": op, "a": a, "b": b, "result": result})
        return result


def parse_expression(raw):
    """Parse ``a op b`` and evaluate it with a Calculator.

    An empty string (or whitespace only) is accepted here and handed straight
    to the operator, which is the upstream cause of the failing test.
    """
    tokens = (raw or "").split()
    if len(tokens) != 3:
        raise CalculatorError(f"cannot parse expression: {raw!r}")

    left, op, right = tokens
    a, b = float(left), float(right)
    calc = Calculator()

    if op == "+":
        return calc.add(a, b)
    if op == "-":
        return calc.sub(a, b)
    if op == "*":
        return calc.mul(a, b)
    if op == "/":
        return calc.div(a, b)
    raise CalculatorError(f"unsupported operator: {op}")
