"""Exact money handling for the susu tracker.

Money is stored internally as a whole number of pesewas (1 GHS = 100 pesewas).
Keeping the value as an integer means arithmetic is always exact: there are no
floating point rounding errors. Amounts entered as text such as "50.00" are
parsed through :class:`decimal.Decimal` so the conversion is exact as well.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from functools import total_ordering

PESEWAS_PER_CEDI = 100


@total_ordering
class Money:
    """An exact amount of Ghana cedis, held as an integer number of pesewas."""

    __slots__ = ("pesewas",)

    def __init__(self, pesewas: int) -> None:
        if not isinstance(pesewas, int) or isinstance(pesewas, bool):
            raise TypeError("pesewas must be a plain integer")
        self.pesewas = pesewas

    @classmethod
    def from_pesewas(cls, pesewas: int) -> "Money":
        """Build money from a whole number of pesewas."""
        return cls(pesewas)

    @classmethod
    def parse(cls, text: object) -> "Money":
        """Parse a cedis amount such as "50" or "50.00" into Money.

        The amount may have at most two decimal places because a pesewa is the
        smallest unit of currency. More precise input is rejected rather than
        silently rounded.
        """
        try:
            value = Decimal(str(text).strip())
        except (InvalidOperation, ValueError):
            raise ValueError("amount is not a valid number: %r" % (text,))

        if not value.is_finite():
            raise ValueError("amount must be a finite number")

        if value.as_tuple().exponent < -2:
            raise ValueError("amount cannot be more precise than one pesewa")

        pesewas = int(value.scaleb(2).to_integral_value())
        return cls(pesewas)

    def to_decimal(self) -> Decimal:
        """Return the amount as a Decimal in cedis, for example Decimal("50.00")."""
        return (Decimal(self.pesewas) / PESEWAS_PER_CEDI).quantize(Decimal("0.01"))

    def is_zero(self) -> bool:
        return self.pesewas == 0

    def is_negative(self) -> bool:
        return self.pesewas < 0

    def is_positive(self) -> bool:
        return self.pesewas > 0

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.pesewas + other.pesewas)

    def __sub__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.pesewas - other.pesewas)

    def __mul__(self, count: int) -> "Money":
        if not isinstance(count, int) or isinstance(count, bool):
            return NotImplemented
        return Money(self.pesewas * count)

    __rmul__ = __mul__

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.pesewas == other.pesewas

    def __lt__(self, other: "Money") -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.pesewas < other.pesewas

    def __hash__(self) -> int:
        return hash(self.pesewas)

    def __str__(self) -> str:
        sign = "-" if self.pesewas < 0 else ""
        whole, part = divmod(abs(self.pesewas), PESEWAS_PER_CEDI)
        return "GHS %s%d.%02d" % (sign, whole, part)

    def __repr__(self) -> str:
        return "Money.from_pesewas(%d)" % self.pesewas
