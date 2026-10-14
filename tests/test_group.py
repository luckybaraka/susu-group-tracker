"""Tests for the group rules and validation.

These cover the rejection rules the instructions call out: unknown members,
duplicate members, zero or negative amounts, and payments above what a member
owes for the week.
"""

import unittest

from susu.errors import (
    DuplicateMemberError,
    UnknownMemberError,
    ValidationError,
)
from susu.group import SusuGroup
from susu.money import Money


def make_group(amount="50.00"):
    return SusuGroup("Test Group", Money.parse(amount))


class GroupCreationTests(unittest.TestCase):
    def test_rejects_non_positive_weekly_amount(self):
        with self.assertRaises(ValidationError):
            SusuGroup("Test", Money.parse("0"))
        with self.assertRaises(ValidationError):
            SusuGroup("Test", Money.from_pesewas(-100))

    def test_rejects_empty_group_name(self):
        with self.assertRaises(ValidationError):
            SusuGroup("   ", Money.parse("50.00"))


class MemberRuleTests(unittest.TestCase):
    def test_adds_members_in_join_order(self):
        group = make_group()
        group.add_member("Ama")
        group.add_member("Kofi")
        group.add_member("Esi")
        self.assertEqual(group.members, ["Ama", "Kofi", "Esi"])

    def test_rejects_duplicate_member(self):
        group = make_group()
        group.add_member("Ama")
        with self.assertRaises(DuplicateMemberError):
            group.add_member("Ama")

    def test_rejects_empty_member_name(self):
        group = make_group()
        with self.assertRaises(ValidationError):
            group.add_member("   ")

    def test_cannot_add_member_after_group_has_started(self):
        group = make_group()
        group.add_member("Ama")
        group.record_contribution("Ama", Money.parse("50.00"))
        group.close_week()  # week 1 closes, the group has now started
        with self.assertRaises(ValidationError):
            group.add_member("Latecomer")


class ContributionRuleTests(unittest.TestCase):
    def setUp(self):
        self.group = make_group()
        for name in ["Ama", "Kofi", "Esi"]:
            self.group.add_member(name)

    def test_rejects_unknown_member(self):
        with self.assertRaises(UnknownMemberError):
            self.group.record_contribution("Yaa", Money.parse("50.00"))

    def test_rejects_zero_amount(self):
        with self.assertRaises(ValidationError):
            self.group.record_contribution("Ama", Money.from_pesewas(0))

    def test_rejects_negative_amount(self):
        with self.assertRaises(ValidationError):
            self.group.record_contribution("Ama", Money.from_pesewas(-500))

    def test_rejects_payment_above_amount_owed(self):
        with self.assertRaises(ValidationError):
            self.group.record_contribution("Ama", Money.parse("50.01"))

    def test_rejects_second_payment_that_would_exceed_the_week(self):
        self.group.record_contribution("Ama", Money.parse("40.00"))
        with self.assertRaises(ValidationError):
            self.group.record_contribution("Ama", Money.parse("20.00"))

    def test_rejects_recording_for_a_non_current_week(self):
        with self.assertRaises(ValidationError):
            self.group.record_contribution("Ama", Money.parse("50.00"), week=2)

    def test_partial_payment_is_allowed_and_tracked(self):
        remaining = self.group.record_contribution("Esi", Money.parse("30.00"))
        self.assertEqual(remaining, Money.parse("20.00"))
        self.assertEqual(self.group.amount_paid("Esi"), Money.parse("30.00"))
        self.assertEqual(self.group.amount_owed("Esi"), Money.parse("20.00"))


if __name__ == "__main__":
    unittest.main()
