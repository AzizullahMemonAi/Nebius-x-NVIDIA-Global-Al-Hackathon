import unittest

from calculator import Calculator, CalculatorError, parse_expression


class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = Calculator()

    def test_add(self):
        self.assertEqual(self.calc.add(2, 3), 5)

    def test_sub(self):
        self.assertEqual(self.calc.sub(5, 3), 2)

    def test_mul(self):
        self.assertEqual(self.calc.mul(4, 3), 12)

    def test_div_by_zero_raises_calculator_error(self):
        # Expected: CalculatorError. Actual: ZeroDivisionError escapes.
        with self.assertRaises(CalculatorError):
            self.calc.div(1, 0)

    def test_empty_expression_is_rejected(self):
        # Expected: CalculatorError. Actual: parse error is masked by the
        # division path when the expression is empty.
        with self.assertRaises(CalculatorError):
            parse_expression("   ")


if __name__ == "__main__":
    unittest.main()
