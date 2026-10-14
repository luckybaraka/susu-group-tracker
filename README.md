# Susu Group Tracker

A small command line program that manages one rotating savings group (susu).

In a susu, a group of members each pay the same fixed amount every week. Each
week the whole pot is paid to one member. Members receive the pot in the order
they joined, one member per week. The cycle runs for as many weeks as there are
members, so everyone receives the pot exactly once.

## What it does

- Create a group with a fixed weekly contribution in GHS.
- Add members by unique name.
- Record contributions for the current week, including partial payments.
- Close a week: if everyone has paid in full, pay the pot to the next member in
  join order and move to the next week; otherwise pay nothing and report who
  still owes and how much.
- Show a report: the current week, who has paid in full, who owes what, and the
  payout history.

Money is handled exactly. Amounts are stored internally as whole pesewas
(1 GHS = 100 pesewas), so there are no floating point rounding errors.

## Requirements

- Python 3.9 or newer.
- No third party packages. The program uses only the Python standard library.

## How to run

Run the program as a module from the repository root. State is kept in a JSON
file (default `susu_state.json` in the current directory). Use `--state` to
choose a different file.

```
python -m susu init --name "Market Women" --amount 50.00
python -m susu add-member --name Ama
python -m susu add-member --name Kofi
python -m susu add-member --name Esi
python -m susu pay --member Ama --amount 50.00
python -m susu pay --member Kofi --amount 50.00
python -m susu pay --member Esi --amount 30.00
python -m susu close-week
python -m susu report
```

### Commands

| Command        | What it does                                              |
| -------------- | -------------------------------------------------------- |
| `init`         | Create a new group. Needs `--name` and `--amount`.       |
| `add-member`   | Add a member. Needs `--name`.                            |
| `pay`          | Record a contribution. Needs `--member` and `--amount`.  |
| `close-week`   | Try to close the current week and pay out the pot.       |
| `report`       | Show the current week, who is paid up, who owes, history. |

Global option `--state PATH` selects the state file. The `init` command refuses
to overwrite an existing state file unless you pass `--force`.

### Worked example

Using the commands above with three members (Ama, Kofi, Esi) and a weekly
amount of 50.00:

- Ama and Kofi pay 50.00. Esi pays only 30.00.
- `close-week` pays nothing and reports that Esi owes 20.00.
- Esi pays the remaining 20.00. `close-week` now pays the pot of 150.00 to Ama
  and moves to week 2, where Kofi is next to receive the pot.

## How to run the tests

From the repository root:

```
python -m unittest discover -s tests
```

For more detail, add `-v`. There are over thirty tests covering exact money
handling, every validation rule, the partial payment case, the week-cannot-close
case, a full rotation, and the command line interface end to end.

## Project layout

```
susu/
  money.py      Exact money value object (integer pesewas).
  errors.py     Error types for business rule violations.
  group.py      The susu group and all business rules.
  storage.py    Atomic load and save of group state to JSON.
  cli.py        Command line interface.
  __main__.py   Entry point for "python -m susu".
tests/
  test_money.py     Money handling.
  test_group.py     Member and contribution validation.
  test_rotation.py  Week closing, payout and full rotation.
  test_cli.py       End-to-end command line tests.
```

See `NOTES.md` for the assumptions and design decisions behind the rules.
