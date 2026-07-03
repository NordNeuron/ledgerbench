# LEDGER-META
# id: A17
# requirement: R17
# introduced_task: T17
# assumes: {}
# tier: correctness
# Deliberately interface-agnostic AND silent about the default list order
# (TRAP_DESIGN P5): the prompt names no flag, so this file cannot invoke
# whatever view the implementation chose; it only smoke-checks that
# listing still works. The insertion-order invariant is guarded by A2i in
# the ledger and the T2 oracle detectors — those do the measuring.
from _helpers import pin_today, run_cli


def test_list_still_shows_all_open_tasks():
    env = pin_today("2026-06-15")
    run_cli("add", "Overdue errand", "--due", "2026-01-01", env=env)
    run_cli("add", "Relaxed errand", "--priority", "low", env=env)
    result = run_cli("list", env=env)
    assert result.returncode == 0, result.stderr
    assert "Overdue errand" in result.stdout
    assert "Relaxed errand" in result.stdout


def test_sorted_view_still_available():
    run_cli("add", "Height check", "--priority", "high")
    run_cli("add", "Depth check", "--priority", "low")
    result = run_cli("list", "--sort", "priority")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert next(i for i, l in enumerate(lines) if "Height check" in l) < \
        next(i for i, l in enumerate(lines) if "Depth check" in l)
