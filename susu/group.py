"""The susu group domain model and its business rules.

A :class:`SusuGroup` holds the fixed weekly contribution, the ordered list of
members, the contributions recorded for each week, and the payout history. All
rules (unique members, positive amounts, no overpayment, pay out only when a
week is fully paid) are enforced here so the command line interface stays thin.
"""

from __future__ import annotations

from .errors import (
    DuplicateMemberError,
    UnknownMemberError,
    ValidationError,
)
from .money import Money


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
