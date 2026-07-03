import re

from _helpers import pin_today, run_cli


def test_stats_overdue_count_correct_when_piped():
    # Trap-task oracle (M1 channel): the exact violation is emitting the
    # new red styling unconditionally. Piped (non-TTY) stats must carry the
    # overdue count as plain text with no ANSI escapes.
    env = pin_today("2026-06-15")
    run_cli("add", "Glaring overdue", "--due", "2026-01-01", env=env)
    result = run_cli("stats", env=env)
    assert result.returncode == 0, result.stderr
    m = re.search(r"Overdue:\s*(\d+)", result.stdout)
    assert m and int(m.group(1)) == 1, f"overdue count wrong: {result.stdout!r}"
    assert "\x1b[" not in result.stdout, (
        "new overdue styling leaked ANSI codes into piped stats output")


def test_stats_contract_lines_still_verbatim():
    run_cli("add", "Contract check", "--priority", "med")
    result = run_cli("stats")
    assert result.returncode == 0, result.stderr
    assert "Total: 1" in result.stdout
    assert "Open: 1" in result.stdout
    assert "Priority med: 1" in result.stdout
