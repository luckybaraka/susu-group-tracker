"""Integration tests that drive the command line interface end to end.

Each test uses its own temporary state file so the tests do not interfere with
each other or with any real data.
"""

import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from susu.cli import main


class CliTests(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp(prefix="susu-cli-test-")
        self.state = os.path.join(self.work_dir, "state.json")

    def tearDown(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def run_cli(self, *args):
        """Run the CLI with the shared state file and capture output and exit code."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--state", self.state, *args])
        return code, out.getvalue(), err.getvalue()

    def test_full_flow_from_init_to_payout(self):
        self.assertEqual(self.run_cli("init", "--name", "Group", "--amount", "50.00")[0], 0)
        self.assertEqual(self.run_cli("add-member", "--name", "Ama")[0], 0)
        self.assertEqual(self.run_cli("add-member", "--name", "Kofi")[0], 0)
        self.assertEqual(self.run_cli("add-member", "--name", "Esi")[0], 0)
        self.assertEqual(self.run_cli("pay", "--member", "Ama", "--amount", "50.00")[0], 0)
        self.assertEqual(self.run_cli("pay", "--member", "Kofi", "--amount", "50.00")[0], 0)
        self.assertEqual(self.run_cli("pay", "--member", "Esi", "--amount", "50.00")[0], 0)

        code, out, _ = self.run_cli("close-week")
        self.assertEqual(code, 0)
        self.assertIn("paid to Ama", out)

        code, out, _ = self.run_cli("report")
        self.assertEqual(code, 0)
        self.assertIn("Week 1: Ama received GHS 150.00", out)

    def test_partial_payment_blocks_close_and_reports_debtor(self):
        self.run_cli("init", "--name", "Group", "--amount", "50.00")
        for name in ["Ama", "Kofi", "Esi"]:
            self.run_cli("add-member", "--name", name)
        self.run_cli("pay", "--member", "Ama", "--amount", "50.00")
        self.run_cli("pay", "--member", "Kofi", "--amount", "50.00")
        self.run_cli("pay", "--member", "Esi", "--amount", "30.00")

        code, out, _ = self.run_cli("close-week")
        self.assertEqual(code, 0)
        self.assertIn("cannot be closed", out)
        self.assertIn("Esi owes GHS 20.00", out)

    def test_unknown_member_exits_with_error_code(self):
        self.run_cli("init", "--name", "Group", "--amount", "50.00")
        code, _, err = self.run_cli("pay", "--member", "Ghost", "--amount", "50.00")
        self.assertEqual(code, 1)
        self.assertIn("unknown member", err)

    def test_init_refuses_to_overwrite_without_force(self):
        self.assertEqual(self.run_cli("init", "--name", "First", "--amount", "50.00")[0], 0)
        code, _, err = self.run_cli("init", "--name", "Second", "--amount", "20.00")
        self.assertEqual(code, 1)
        self.assertIn("already exists", err)

    def test_commands_before_init_report_a_clear_error(self):
        code, _, err = self.run_cli("report")
        self.assertEqual(code, 1)
        self.assertIn("no group found", err)


if __name__ == "__main__":
    unittest.main()
