"""Command line interface for the susu tracker.

Each command is a separate run of the program that loads the group from a JSON
state file, makes one change, and saves it again. This keeps the interface
simple and scriptable. Use ``--state`` to point at a different file, which is
how the tests drive the CLI without touching each other's data.

Commands:
    init         Create a new group with a weekly contribution amount.
    add-member   Add a member by unique name.
    pay          Record a contribution for a member for the current week.
    close-week   Try to close the current week and pay out the pot.
    report       Show the current week, who is paid up, who owes, and history.
"""

from __future__ import annotations

import argparse
import os
import sys

from .errors import SusuError, ValidationError
from .group import Report, SusuGroup
from .money import Money

DEFAULT_STATE_FILE = "susu_state.json"


def _parse_amount(text: str) -> Money:
    """Parse a money amount from the command line into Money."""
    try:
        return Money.parse(text)
    except ValueError as error:
        raise ValidationError(str(error))


def _require_group(path: str) -> SusuGroup:
    """Load the group at ``path`` or raise a clear error if there is none."""
    from .storage import load_group

    group = load_group(path)
    if group is None:
        raise ValidationError(
            "no group found at %s (run 'init' first)" % path
        )
    return group


def cmd_init(args: argparse.Namespace) -> None:
    from .storage import save_group

    if os.path.exists(args.state) and not args.force:
        raise ValidationError(
            "state file already exists: %s (use --force to overwrite)" % args.state
        )
    group = SusuGroup(args.name, _parse_amount(args.amount))
    save_group(group, args.state)
    print(
        "Created group '%s' with weekly contribution %s."
        % (group.name, group.weekly_amount)
    )
    print("State saved to %s" % args.state)


def cmd_add_member(args: argparse.Namespace) -> None:
    from .storage import save_group

    group = _require_group(args.state)
    name = group.add_member(args.name)
    save_group(group, args.state)
    count = len(group.members)
    word = "member" if count == 1 else "members"
    print("Added member '%s'. The group now has %d %s." % (name, count, word))


def cmd_pay(args: argparse.Namespace) -> None:
    from .storage import save_group

    group = _require_group(args.state)
    amount = _parse_amount(args.amount)
    remaining = group.record_contribution(args.member, amount, week=args.week)
    save_group(group, args.state)
    if remaining.is_zero():
        print(
            "Recorded %s from %s for week %d. %s has now paid in full."
            % (amount, args.member, group.current_week, args.member)
        )
    else:
        print(
            "Recorded %s from %s for week %d. %s still owes %s."
            % (amount, args.member, group.current_week, args.member, remaining)
        )


def cmd_close_week(args: argparse.Namespace) -> None:
    from .storage import save_group

    group = _require_group(args.state)
    result = group.close_week()
    save_group(group, args.state)
    if result.closed:
        print(
            "Week %d closed. The pot of %s was paid to %s."
            % (result.week, result.payout, result.recipient)
        )
        if group.is_complete():
            print("Every member has now received the pot. The group is complete.")
        else:
            print(
                "Week %d is now open. %s is next to receive the pot."
                % (group.current_week, group.next_recipient())
            )
    else:
        print("Week %d cannot be closed. The following members still owe:" % result.week)
        for debtor in result.debtors:
            print("  %s owes %s" % (debtor.name, debtor.owed))


def cmd_report(args: argparse.Namespace) -> None:
    group = _require_group(args.state)
    _print_report(group.report())


def _print_report(report: Report) -> None:
    """Print a human readable report for the current state of the group."""
    print("Group:   %s" % report.group_name)
    print("Weekly:  %s" % report.weekly_amount)
    print("Pot:     %s per week" % report.pot)

    if report.complete:
        print("Status:  complete (every member has received the pot)")
    else:
        print("Week:    %d (open)" % report.current_week)
        print("Next to receive the pot: %s" % report.next_recipient)
        print("")
        print("Paid in full this week:")
        paid = [status for status in report.statuses if status.paid_in_full]
        if paid:
            for status in paid:
                print("  %s (%s)" % (status.name, status.paid))
        else:
            print("  nobody yet")
        print("")
        print("Still owing this week:")
        owing = [status for status in report.statuses if not status.paid_in_full]
        if owing:
            for status in owing:
                print("  %s owes %s (paid %s)" % (status.name, status.owed, status.paid))
        else:
            print("  nobody, the week is ready to close")

    print("")
    print("Payout history:")
    if report.payouts:
        for payout in report.payouts:
            print(
                "  Week %d: %s received %s"
                % (payout["week"], payout["member"], payout["amount"])
            )
    else:
        print("  no payouts yet")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="susu",
        description="Manage one rotating savings group (susu).",
    )
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE_FILE,
        help="path to the JSON state file (default: %s)" % DEFAULT_STATE_FILE,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create a new group")
    init_parser.add_argument("--name", required=True, help="group name")
    init_parser.add_argument(
        "--amount", required=True, help="fixed weekly contribution, for example 50.00"
    )
    init_parser.add_argument(
        "--force", action="store_true", help="overwrite an existing state file"
    )
    init_parser.set_defaults(handler=cmd_init)

    add_parser = subparsers.add_parser("add-member", help="add a member")
    add_parser.add_argument("--name", required=True, help="unique member name")
    add_parser.set_defaults(handler=cmd_add_member)

    pay_parser = subparsers.add_parser("pay", help="record a contribution")
    pay_parser.add_argument("--member", required=True, help="member name")
    pay_parser.add_argument("--amount", required=True, help="amount paid, for example 50.00")
    pay_parser.add_argument(
        "--week",
        type=int,
        default=None,
        help="week to record for (defaults to the current open week)",
    )
    pay_parser.set_defaults(handler=cmd_pay)

    close_parser = subparsers.add_parser("close-week", help="try to close the current week")
    close_parser.set_defaults(handler=cmd_close_week)

    report_parser = subparsers.add_parser("report", help="show the group report")
    report_parser.set_defaults(handler=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Returns a process exit code (0 on success, 1 on a rule error)."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.handler(args)
    except SusuError as error:
        print("Error: %s" % error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
