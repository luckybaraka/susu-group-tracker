# Notes: assumptions, decisions, and future work

This file explains the choices I made, especially for the cases the
instructions left open.

## Money

- Money is stored as a whole number of pesewas (1 GHS = 100 pesewas). All
  arithmetic is integer arithmetic, so there are no floating point rounding
  errors. This directly meets the "money must be handled exactly" rule.
- Amounts typed by a user (such as `50.00`) are parsed through `Decimal` and
  then converted to pesewas. Input more precise than one pesewa (for example
  `50.001`) is rejected rather than silently rounded.

## Member identity

- A member is identified by a unique name. Surrounding whitespace is trimmed,
  but the name is otherwise case sensitive, so `Ama` and `ama` are two
  different members. In a real deployment I would likely assign a separate ID
  and allow the display name to repeat, but for this exercise a unique name is
  the simplest clear identifier.

## Cases the instructions did not cover

These are my decisions. Each one is enforced in code.

1. **Adding a member after the group has started.** Members may be added at any
   time during week 1, up to the moment week 1 is closed and the first payout is
   made. Once any money has been paid out, the rotation order is fixed and
   membership is locked. This keeps the payout order fair: nobody can join after
   payouts have begun and jump the queue or change the pot for weeks that have
   already paid out. A member added during week 1 owes the weekly amount for
   week 1 like everyone else and is placed at the end of the payout order.

2. **Which week a contribution applies to.** Contributions can only be recorded
   for the current open week. Earlier weeks are already settled, and later weeks
   are not open yet. This prevents editing history and keeps each week's balance
   easy to reason about. The CLI still accepts an explicit `--week`, but it must
   match the current week or it is rejected.

3. **Overpayment.** A payment cannot exceed what the member still owes for the
   current week. The check is exact to the pesewa, so a member who owes 20.00
   cannot pay 20.01.

4. **Length of the cycle.** The cycle runs for exactly as many weeks as there
   are members, so each member receives the pot exactly once. After the final
   payout the group is marked complete, and any further contribution or week
   close is rejected. Starting a new cycle would be a separate group.

5. **The pot.** The pot for a week is the weekly amount multiplied by the number
   of members. Over a full cycle each member pays that same total in and
   receives it once, so the susu nets to zero for everyone.

## State and safety

- The CLI stores one group per JSON state file. Saving is atomic: the new state
  is written to a temporary file and then moved into place, so an interrupted
  save cannot leave a corrupt file behind.
- Business rule violations raise a typed error that the CLI turns into a clear
  message and a non-zero exit code. Bad input never produces a traceback.
- The program assumes a single user running commands one at a time. There is no
  locking against two processes writing the same state file at once.

## What I would improve with more time

- Handle a member who defaults: a rule for what happens when someone never
  finishes paying a week (for example, cover from a reserve, or reorder).
- Support more than one group, and a way to start a new cycle for the same
  members after one completes.
- Track real dates for each week instead of abstract week numbers, and record a
  timestamped audit log of every action.
- Richer reports: total paid in and received per member across the whole cycle.
- Package the project with `pyproject.toml` and a `susu` console entry point.
- Add file locking so concurrent runs cannot corrupt shared state.
