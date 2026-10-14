"""Exceptions raised by the susu tracker.

All business rule violations raise :class:`SusuError` (or a subclass). The
command line interface catches this type and prints a clear message instead of
a traceback, so bad input never crashes the program.
"""

from __future__ import annotations


class SusuError(Exception):
    """Base class for every error the susu tracker raises on purpose."""


class ValidationError(SusuError):
    """Raised when input breaks a rule, for example a negative amount."""


class UnknownMemberError(ValidationError):
    """Raised when an action refers to a member who is not in the group."""


class DuplicateMemberError(ValidationError):
    """Raised when adding a member whose name already exists in the group."""
