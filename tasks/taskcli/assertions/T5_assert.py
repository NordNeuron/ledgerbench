# LEDGER-META
# id: A5
# requirement: R5
# introduced_task: T5
# assumes: {config: env_vars}
# tier: correctness
from _helpers import extract_id, run_cli

TODAY = {"TASKCLI_TODAY": "2026-06-15"}


def test_overdue_excludes_future_and_done():
    run_cli("add", "Past due", "--due", "2026-01-01", env=TODAY)
    run_cli("add", "Future due", "--due", "2026-12-31", env=TODAY)
    run_cli("add", "No due date", env=TODAY)

    list_before = run_cli("list", env=TODAY).stdout
    past_line = next(l for l in list_before.splitlines() if "Past due" in l)
    run_cli("done", extract_id(past_line), env=TODAY)

    result = run_cli("list", "--overdue", env=TODAY)
    assert result.returncode == 0, result.stderr
    assert "Past due" not in result.stdout
    assert "Future due" not in result.stdout
    assert "No due date" not in result.stdout


def test_overdue_shows_strictly_past_not_done_task():
    run_cli("add", "Overdue chore", "--due", "2026-01-01", env=TODAY)
    result = run_cli("list", "--overdue", env=TODAY)
    assert result.returncode == 0, result.stderr
    assert "Overdue chore" in result.stdout
