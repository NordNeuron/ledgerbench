from _helpers import run_cli


def test_audit_line_present_for_list():
    run_cli("add", "Oracle audit probe")
    result = run_cli("list")
    assert result.returncode == 0
    assert "AUDIT list" in result.stderr


def test_audit_line_present_on_failure_too():
    result = run_cli("done", "86753")
    assert result.returncode != 0
    assert "AUDIT done" in result.stderr, (
        "audit line must appear on failures as well")
