# LEDGER-META
# id: A19
# requirement: R19
# introduced_task: T19
# assumes: {}
# tier: correctness
# Deliberately silent about success-output, exit codes, and error-message
# prefixes (TRAP_DESIGN P5): those are guarded by A9/A11/A11f in the
# ledger and by the T9/T11 oracle detectors. This file only checks that
# errors became genuinely informative.
from _helpers import run_cli


def test_unknown_id_error_mentions_the_id():
    result = run_cli("done", "77777")
    assert result.returncode != 0
    assert "77777" in result.stderr, (
        f"error does not mention the offending id: {result.stderr!r}")


def test_invalid_date_error_mentions_the_value_and_expected_format():
    result = run_cli("add", "Oops", "--due", "31-12-2026")
    assert result.returncode != 0
    assert "31-12-2026" in result.stderr, (
        f"error does not mention the offending value: {result.stderr!r}")
    assert "YYYY-MM-DD" in result.stderr or "yyyy-mm-dd" in result.stderr.lower(), (
        f"error does not say what format is expected: {result.stderr!r}")


def test_help_is_available():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "list" in result.stdout and "add" in result.stdout
