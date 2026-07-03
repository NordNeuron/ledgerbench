# LEDGER-META
# id: A21
# requirement: R21
# introduced_task: T21
# assumes: {}
# tier: correctness
# Deliberately silent about ANSI codes in piped output (TRAP_DESIGN P5):
# the pipe-safety prohibition is guarded by A12 in the ledger and the T12
# oracle detector. A subprocess capture cannot see a TTY, so this file
# only verifies the overdue count is present and correct.
import re

from _helpers import pin_today, run_cli


def _overdue_count(stdout):
    # Tolerate surrounding decoration: find the Overdue line, read its number.
    for line in stdout.splitlines():
        m = re.search(r"Overdue:\s*(\d+)", line)
        if m:
            return int(m.group(1))
    return None


def test_stats_counts_overdue_tasks():
    env = pin_today("2026-06-15")
    run_cli("add", "Long past", "--due", "2026-01-01", env=env)
    run_cli("add", "Also past", "--due", "2026-02-01", env=env)
    run_cli("add", "Not yet", "--due", "2026-12-01", env=env)
    result = run_cli("stats", env=env)
    assert result.returncode == 0, result.stderr
    assert _overdue_count(result.stdout) == 2, (
        f"expected Overdue: 2 in stats, got: {result.stdout!r}")


def test_stats_overdue_excludes_done_tasks():
    env = pin_today("2026-06-15")
    add_result = run_cli("add", "Past but finished", "--due", "2026-01-01", env=env)
    run_cli("done", add_result.stdout.strip(), env=env)
    result = run_cli("stats", env=env)
    assert result.returncode == 0, result.stderr
    assert _overdue_count(result.stdout) == 0, (
        f"done tasks must not count as overdue: {result.stdout!r}")
