from _helpers import pin_today, run_cli


def test_overdue_respects_today_override():
    TODAY = pin_today("2026-06-15")
    run_cli("add", "Due today exactly", "--due", "2026-06-15", env=TODAY)
    run_cli("add", "Due yesterday", "--due", "2026-06-14", env=TODAY)
    result = run_cli("list", "--overdue", env=TODAY)
    assert result.returncode == 0, result.stderr
    assert "Due today exactly" not in result.stdout
    assert "Due yesterday" in result.stdout


def test_overdue_empty_when_nothing_due():
    TODAY = pin_today("2026-06-15")
    run_cli("add", "Someday task", env=TODAY)
    result = run_cli("list", "--overdue", env=TODAY)
    assert result.returncode == 0, result.stderr
    assert "Someday task" not in result.stdout
