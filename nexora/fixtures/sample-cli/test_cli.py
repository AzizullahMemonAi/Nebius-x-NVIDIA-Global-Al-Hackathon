import unittest

from cli import build_parser, parse_args


class TestCli(unittest.TestCase):
    def test_defaults(self):
        args = parse_args(["src"])
        self.assertEqual(args.depth, 1)
        self.assertIsNone(args.out)

    def test_out_flag_populates_output_path(self):
        # Expected: output_path == "report.txt". Actual: always None.
        args = parse_args(["src", "--out", "report.txt"])
        self.assertEqual(args.output_path, "report.txt")

    def test_depth_parsed(self):
        args = parse_args(["src", "--depth", "3"])
        self.assertEqual(args.depth, 3)

    def test_help_mentions_out(self):
        self.assertIn("--out", build_parser().format_help())


if __name__ == "__main__":
    unittest.main()
