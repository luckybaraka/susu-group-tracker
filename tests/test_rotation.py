"""Tests for closing weeks, paying out the pot, and the full rotation.

Includes the two cases the instructions name directly: the partial payment case
and the case where a week cannot close because someone still owes.
"""

import unittest

from susu.errors import ValidationError
from susu.group import SusuGroup
from susu.money import Money


def make_started_group(members=("Ama", "Kofi", "Esi"), amount="50.00"):
    group = SusuGroup("Test Group", Money.parse(amount))
    for name in members:
        group.add_member(name)
    return group


class WeekCannotCloseTests(unittest.TestCase):
    def test_week_cannot_close_when_a_member_only_paid_partially(self):
        group = make_started_group()
        group.record_contribution("Ama", Money.parse("50.00"))
        group.record_contribution("Kofi", Money.parse("50.00"))
        group.record_contribution("Esi", Money.parse("30.00"))

        result = group.close_week()

        self.assertFalse(result.closed)
        self.assertEqual(result.week, 1)
        self.assertEqual(len(result.debtors), 1)
        self.assertEqual(result.debtors[0].name, "Esi")
        self.assertEqual(result.debtors[0].owed, Money.parse("20.00"))
        # Nothing was paid out and the week did not advance.
        self.assertEqual(group.payouts, [])
        self.assertEqual(group.current_week, 1)

    def test_cannot_close_a_week_with_no_members(self):
        group = SusuGroup("Empty", Money.parse("50.00"))
        with self.assertRaises(ValidationError):
            group.close_week()


class WorkedExampleTests(unittest.TestCase):
    def test_reproduces_the_instructions_example(self):
        group = make_started_group()
        group.record_contribution("Ama", Money.parse("50.00"))
        group.record_contribution("Kofi", Money.parse("50.00"))
        group.record_contribution("Esi", Money.parse("30.00"))

        # Closing week 1 pays nothing because Esi still owes 20.00.
        first = group.close_week()
        self.assertFalse(first.closed)

        # Esi pays the remaining 20.00 and the week closes.
        group.record_contribution("Esi", Money.parse("20.00"))
        second = group.close_week()

        self.assertTrue(second.closed)
        self.assertEqual(second.recipient, "Ama")
        self.assertEqual(second.payout, Money.parse("150.00"))
        # Week 2 begins and Kofi is next.
        self.assertEqual(group.current_week, 2)
        self.assertEqual(group.next_recipient(), "Kofi")


class FullRotationTests(unittest.TestCase):
    def test_every_member_receives_the_pot_once_in_join_order(self):
        group = make_started_group()
        received = []
        for _ in range(len(group.members)):
            for member in group.members:
                group.record_contribution(member, Money.parse("50.00"))
            result = group.close_week()
            self.assertTrue(result.closed)
            received.append(result.recipient)

        self.assertEqual(received, ["Ama", "Kofi", "Esi"])
        self.assertTrue(group.is_complete())

    def test_closing_after_completion_is_rejected(self):
        group = make_started_group(members=("Ama",))
        group.record_contribution("Ama", Money.parse("50.00"))
        group.close_week()  # Ama receives the pot, the one-member cycle is done
        self.assertTrue(group.is_complete())
        with self.assertRaises(ValidationError):
            group.close_week()

    def test_cannot_record_after_completion(self):
        group = make_started_group(members=("Ama",))
        group.record_contribution("Ama", Money.parse("50.00"))
        group.close_week()
        with self.assertRaises(ValidationError):
            group.record_contribution("Ama", Money.parse("50.00"))

    def test_report_shows_payout_history_after_a_payout(self):
        group = make_started_group()
        for member in group.members:
            group.record_contribution(member, Money.parse("50.00"))
        group.close_week()

        report = group.report()
        self.assertEqual(len(report.payouts), 1)
        self.assertEqual(report.payouts[0]["member"], "Ama")
        self.assertEqual(report.payouts[0]["amount"], Money.parse("150.00"))
        self.assertEqual(report.next_recipient, "Kofi")


if __name__ == "__main__":
    unittest.main()
