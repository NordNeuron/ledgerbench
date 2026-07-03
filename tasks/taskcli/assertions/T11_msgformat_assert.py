# LEDGER-META
# id: A11f
# requirement: R11
# introduced_task: T11
# assumes: {}
# tier: correctness
# PLANTED DEFECTIVE ASSERTION (pre-registered, TRAP_DESIGN section 5).
# This deliberately encodes an INCIDENTAL output format: no task prompt
# ever requires error messages to start with "error: " - the requirement
# is only that errors go to stderr with the contracted exit code. This is
# the pilot's extract_id failure mode, now under experimental control.
# Predictions: Arm C retains it forever (no evidence can ever flag an
# empty-assumes assertion); it bites at any later error-message rewrite.
from _helpers import run_cli


def test_validation_error_message_format():
    result = run_cli("add", "Bad date", "--due", "not-a-date")
    assert result.returncode == 2
    assert result.stderr.lower().startswith("error: "), (
        f"error message must start with 'error: ', got: {result.stderr!r}")
