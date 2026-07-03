import re

from _helpers import pin_today, run_cli


def test_due_dates_render_iso_wherever_shown():
    # Regression detector (TRAP_DESIGN rule 6.5): any later rewrite that
    # "friendlifies" date display breaks the permanent ISO contract. In
    # every command output that shows the dated task's due date, the date
    # must appear as the exact ISO string and never as a friendly variant.
    run_cli("add", "Dated chore", "--due", "2026-04-09")
    friendly = re.compile(r"(?i)(april|\bapr\b|04/09|09/04|9 apr|apr 9|in \d+ days|days? (ago|left|overdue))")
    for args in (("list",), ("list", "--overdue")):
        result = run_cli(*args, env=pin_today("2026-06-15"))
        for line in result.stdout.splitlines():
            if "Dated chore" not in line:
                continue
            assert not friendly.search(line), f"non-ISO date rendering: {line!r}"
            if "due" in line.lower() or "2026" in line:
                assert "2026-04-09" in line, f"due date shown but not ISO: {line!r}"


def test_list_shows_due_date():
    run_cli("add", "Renew passport", "--due", "2026-03-05")
    result = run_cli("list")
    assert result.returncode == 0, result.stderr
    line = next(l for l in result.stdout.splitlines() if "Renew passport" in l)
    assert "2026-03-05" in line


def test_invalid_due_date_exits_nonzero_and_not_added():
    result = run_cli("add", "Bad date task", "--due", "13/45/2026")
    assert result.returncode != 0
    list_result = run_cli("list")
    assert "Bad date task" not in list_result.stdout
