"""Tests for exact money handling.

These tests prove that money is handled exactly, with no rounding errors, which
is one of the explicit requirements.
"""

import unittest
from decimal import Decimal

from susu.money import Money


class MoneyParsingTests(unittest.TestCase):
    def test_parses_whole_and_decimal_amounts(self):
        self.assertEqual(Money.parse("50").pesewas, 5000)
        self.assertEqual(Money.parse("50.00").pesewas, 5000)
        self.assertEqual(Money.parse("0.05").pesewas, 5)
        self.assertEqual(Money.parse("0.01").pesewas, 1)

    def test_rejects_amounts_finer_than_a_pesewa(self):
        with self.assertRaises(ValueError):
            Money.parse("50.001")

    def test_rejects_non_numeric_and_non_finite_input(self):
        for bad in ["abc", "", " ", "nan", "inf", "-inf"]:
            with self.assertRaises(ValueError):
                Money.parse(bad)


class MoneyArithmeticTests(unittest.TestCase):
    def test_addition_and_subtraction_are_exact(self):
        self.assertEqual(Money.parse("50.00") + Money.parse("30.00"), Money.parse("80.00"))
        self.assertEqual(Money.parse("50.00") - Money.parse("30.00"), Money.parse("20.00"))

    def test_repeated_addition_has_no_rounding_error(self):
        # Adding 0.01 one thousand times must equal exactly 10.00.
        total = Money.from_pesewas(0)
        for _ in range(1000):
            total = total + Money.parse("0.01")
        self.assertEqual(total, Money.parse("10.00"))

    def test_multiplication_by_member_count(self):
        self.assertEqual(Money.parse("50.00") * 3, Money.parse("150.00"))

    def test_to_decimal_round_trips(self):
        self.assertEqual(Money.parse("50.00").to_decimal(), Decimal("50.00"))

    def test_comparisons_and_sign_helpers(self):
        self.assertTrue(Money.parse("50.00") > Money.parse("49.99"))
        self.assertTrue(Money.from_pesewas(0).is_zero())
        self.assertTrue(Money.parse("0.01").is_positive())
        self.assertTrue((Money.parse("1.00") - Money.parse("2.00")).is_negative())

    def test_string_format_uses_two_decimal_places(self):
        self.assertEqual(str(Money.parse("50")), "GHS 50.00")
        self.assertEqual(str(Money.parse("0.05")), "GHS 0.05")


if __name__ == "__main__":
    unittest.main()
