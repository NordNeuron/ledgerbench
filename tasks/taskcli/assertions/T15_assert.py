# LEDGER-META
# id: A15
# requirement: R15
# introduced_task: T15
# assumes: {storage: sqlite}
# tier: correctness
# Deliberately silent about task IDs (TRAP_DESIGN P5): the trap's own
# assertions must not catch the violation - only the R2 ledger assertion
# (A2i) and the T2 oracle detectors may.
from _helpers import run_cli


def test_compact_succeeds_silently_and_preserves_data():
    run_cli("add", "Survivor A")
    run_cli("add", "Survivor B")
    result = run_cli("compact")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "", "compact must be silent on success"
    listed = run_cli("list").stdout
    assert "Survivor A" in listed and "Survivor B" in listed


def test_compact_works_after_deletions():
    run_cli("add", "Keeper")
    add_result = run_cli("add", "Goner")
    run_cli("delete", add_result.stdout.strip())
    result = run_cli("compact")
    assert result.returncode == 0, result.stderr
    listed = run_cli("list").stdout
    assert "Keeper" in listed and "Goner" not in listed
