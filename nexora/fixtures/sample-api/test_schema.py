import unittest

from api.schema import ValidationError, validate_name, validate_payload


class TestSchema(unittest.TestCase):
    def test_valid_name(self):
        self.assertEqual(validate_name("  nexus  "), "nexus")

    def test_missing_name(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_name(None)
        self.assertEqual(ctx.exception.code, "name_required")

    def test_non_string_name_uses_validation_error(self):
        # Expected: ValidationError (400). Actual: TypeError (500).
        with self.assertRaises(ValidationError):
            validate_name(12345)

    def test_payload_roundtrip(self):
        cleaned = validate_payload({"name": "nexora", "count": 3})
        self.assertEqual(cleaned, {"name": "nexora", "count": 3})


if __name__ == "__main__":
    unittest.main()
