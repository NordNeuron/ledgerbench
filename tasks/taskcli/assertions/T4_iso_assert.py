# LEDGER-META
# id: A4i
# requirement: R4
# introduced_task: T4
# assumes: {}
# tier: invariant
# NOTE: the ISO rendering IS the requirement here (TRAP_DESIGN 6.1
# format-is-requirement exception): assert exactly the contracted
# property — the date appears as YYYY-MM-DD — and nothing else.
import re

from _helpers import run_cli

ISO_RE = re.compile(r"\b2026-03-05\b")
NON_ISO_HINTS = re.compile(r"(?i)\b(mar|march|03/05|05/03|3/5)\b")


def test_due_date_displayed_as_iso_in_list():
    run_cli("add", "Renew visa", "--due", "2026-03-05")
    result = run_cli("list")
    assert result.returncode == 0, result.stderr
    line = next(l for l in result.stdout.splitlines() if "Renew visa" in l)
    assert ISO_RE.search(line), f"due date not shown as YYYY-MM-DD: {line!r}"
    assert not NON_ISO_HINTS.search(line), f"non-ISO date rendering: {line!r}"
