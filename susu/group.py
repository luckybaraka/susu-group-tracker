"""The susu group domain model and its business rules.

A :class:`SusuGroup` holds the fixed weekly contribution, the ordered list of
members, the contributions recorded for each week, and the payout history. All
rules (unique members, positive amounts, no overpayment, pay out only when a
week is fully paid) are enforced here so the command line interface stays thin.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import (
    DuplicateMemberError,
    UnknownMemberError,
    ValidationError,
)
from .money import Money


@dataclass(frozen=True)
class Debtor:
    """A member who still owes money for a week, and how much they owe."""

    name: str
    owed: Money


@dataclass(frozen=True)
class CloseResult:
    """The outcome of trying to close a week.

    When ``closed`` is True the pot was paid to ``recipient``. When it is False
    no payout happened and ``debtors`` lists who still owes and how much.
    """

    week: int
    closed: bool
    recipient: str | None = None
    payout: Money | None = None
    debtors: tuple[Debtor, ...] = ()


@dataclass(frozen=True)
class MemberStatus:
    """A member's payment position for a single week."""

    name: str
    paid: Money
    owed: Money
    paid_in_full: bool


@dataclass(frozen=True)
class Report:
    """A snapshot of the group: the current week, who is paid up, and history."""

    group_name: str
    weekly_amount: Money
    current_week: int
    complete: bool
    next_recipient: str | None
    pot: Money
    statuses: tuple[MemberStatus, ...]
    payouts: tuple[dict, ...]


class SusuGroup:
    """One rotating savings group.

    Members pay ``weekly_amount`` every week. The whole pot is paid to one
    member per week, in the order the members joined.
    """

    def __init__(self, name: str, weekly_amount: Money) -> None:
        clean_name = name.strip()
        if not clean_name:
            raise ValidationError("group name cannot be empty")
        if not weekly_amount.is_positive():
            raise ValidationError("weekly amount must be greater than zero")

        self.name = clean_name
        self.weekly_amount = weekly_amount
        self.current_week = 1
        # Members in join order. The lookup set gives fast duplicate checks.
        self._members: list[str] = []
        self._member_lookup: set[str] = set()
        # Contributions recorded per week: week number -> member -> amount paid.
        self._contributions: dict[int, dict[str, Money]] = {}
        # Payouts made so far, in order, one per completed week.
        self._payouts: list[dict] = []

    @property
    def members(self) -> list[str]:
        """Return the member names in join order (a copy, so callers cannot edit)."""
        return list(self._members)

    def has_member(self, name: str) -> bool:
        return name.strip() in self._member_lookup

    def has_started(self) -> bool:
        """Return True once collection has begun (week 1 is no longer empty).

        Collection has begun once the group has advanced past week 1. Until
        then the membership can still change.
        """
        return self.current_week > 1

    def add_member(self, name: str) -> str:
        """Add a member by unique name and return the stored name.

        Duplicate names are rejected. Members may only be added before the
        group has started collecting, so that the payout order stays fair.
        """
        clean_name = name.strip()
        if not clean_name:
            raise ValidationError("member name cannot be empty")
        if clean_name in self._member_lookup:
            raise DuplicateMemberError(
                "member already exists: %s" % clean_name
            )
        if self.has_started():
            raise ValidationError(
                "cannot add members after the group has started collecting"
            )

        self._members.append(clean_name)
        self._member_lookup.add(clean_name)
        return clean_name

    def _require_member(self, name: str) -> str:
        """Return the stored member name or raise if the member is unknown."""
        clean_name = name.strip()
        if clean_name not in self._member_lookup:
            raise UnknownMemberError("unknown member: %s" % clean_name)
        return clean_name

    def is_complete(self) -> bool:
        """Return True once every member has received the pot exactly once."""
        return len(self._members) > 0 and len(self._payouts) >= len(self._members)

    def amount_paid(self, name: str, week: int | None = None) -> Money:
        """Return how much a member has paid for the given week (default current)."""
        member = self._require_member(name)
        target_week = self.current_week if week is None else week
        week_record = self._contributions.get(target_week, {})
        return week_record.get(member, Money.from_pesewas(0))

    def amount_owed(self, name: str, week: int | None = None) -> Money:
        """Return how much a member still owes for the given week (default current)."""
        return self.weekly_amount - self.amount_paid(name, week)

    def record_contribution(
        self, name: str, amount: Money, week: int | None = None
    ) -> Money:
        """Record a payment from a member for the current week.

        Partial payments are allowed. The payment is rejected if the member is
        unknown, if the amount is zero or negative, if it is larger than what
        the member still owes this week, if the group is already complete, or if
        the week given is not the current open week. Returns the remaining
        amount the member owes after this payment.
        """
        member = self._require_member(name)

        if self.is_complete():
            raise ValidationError("the group has completed every payout")

        target_week = self.current_week if week is None else week
        if target_week != self.current_week:
            raise ValidationError(
                "contributions can only be recorded for the current week (%d)"
                % self.current_week
            )

        if not amount.is_positive():
            raise ValidationError("contribution amount must be greater than zero")

        owed = self.amount_owed(member, self.current_week)
        if amount > owed:
            raise ValidationError(
                "payment of %s is more than %s still owes this week (%s)"
                % (amount, member, owed)
            )

        week_record = self._contributions.setdefault(self.current_week, {})
        current_paid = week_record.get(member, Money.from_pesewas(0))
        week_record[member] = current_paid + amount
        return owed - amount

    @property
    def payouts(self) -> list[dict]:
        """Return a copy of the payout history, oldest first."""
        return [dict(payout) for payout in self._payouts]

    def next_recipient(self) -> str | None:
        """Return the member due to receive the pot next, or None if complete."""
        if self.is_complete() or not self._members:
            return None
        return self._members[len(self._payouts)]

    def pot_amount(self) -> Money:
        """Return the full pot for one week: weekly amount times member count."""
        return self.weekly_amount * len(self._members)

    def debtors(self, week: int | None = None) -> list[Debtor]:
        """Return the members who still owe money for the given week."""
        target_week = self.current_week if week is None else week
        owing = []
        for member in self._members:
            owed = self.amount_owed(member, target_week)
            if owed.is_positive():
                owing.append(Debtor(member, owed))
        return owing

    def close_week(self) -> CloseResult:
        """Try to close the current week.

        If every member has paid in full, the pot is paid to the next member in
        join order and the group moves to the next week. If anyone still owes,
        nothing is paid out, the week stays open, and the result lists the
        debtors so the caller can report who owes what.
        """
        if not self._members:
            raise ValidationError("cannot close a week with no members")
        if self.is_complete():
            raise ValidationError("the group has completed every payout")

        week = self.current_week
        owing = self.debtors(week)
        if owing:
            return CloseResult(week=week, closed=False, debtors=tuple(owing))

        recipient = self._members[len(self._payouts)]
        pot = self.pot_amount()
        self._payouts.append({"week": week, "member": recipient, "amount": pot})
        self.current_week += 1
        return CloseResult(week=week, closed=True, recipient=recipient, payout=pot)

    def member_statuses(self, week: int | None = None) -> list[MemberStatus]:
        """Return each member's paid and owed amounts for the given week."""
        target_week = self.current_week if week is None else week
        statuses = []
        for member in self._members:
            paid = self.amount_paid(member, target_week)
            owed = self.amount_owed(member, target_week)
            statuses.append(
                MemberStatus(
                    name=member,
                    paid=paid,
                    owed=owed,
                    paid_in_full=not owed.is_positive(),
                )
            )
        return statuses

    def report(self) -> Report:
        """Build a full report of the group's current state and history.

        When the group is complete there is no open week, so the per-member
        statuses are left empty and the payout history tells the full story.
        """
        complete = self.is_complete()
        statuses = () if complete else tuple(self.member_statuses())
        return Report(
            group_name=self.name,
            weekly_amount=self.weekly_amount,
            current_week=self.current_week,
            complete=complete,
            next_recipient=self.next_recipient(),
            pot=self.pot_amount(),
            statuses=statuses,
            payouts=tuple(self.payouts),
        )
