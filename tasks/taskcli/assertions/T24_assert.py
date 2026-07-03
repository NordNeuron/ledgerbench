# LEDGER-META
# id: A24
# requirement: R24
# introduced_task: T24
# assumes: {}
# tier: correctness
# CONFLICT INJECTION (TRAP_DESIGN section 5): R24 (audit line on stderr,
# always) and R9 (done/delete emit NOTHING on success, stderr included)
# are jointly unsatisfiable as written, and no evidence artifact flags
# either side. Expected: Arm B thrashes; Arm C's admission-time conflict
# check escalates to the judge.
from _helpers import extract_id, run_cli


def test_list_emits_one_audit_line():
    run_cli("add", "Audited entry")
    result = run_cli("list")
    assert result.returncode == 0
    audit_lines = [l for l in result.stderr.splitlines() if l.startswith("AUDIT ")]
    assert audit_lines == ["AUDIT list"], (
        f"expected exactly one 'AUDIT list' line on stderr, got {result.stderr!r}")


def test_done_emits_audit_line_on_success():
    run_cli("add", "Audit my completion")
    line = next(l for l in run_cli("list").stdout.splitlines()
                if "Audit my completion" in l)
    result = run_cli("done", extract_id(line))
    assert result.returncode == 0
    assert "AUDIT done" in result.stderr, (
        f"done must audit to stderr even on success, got {result.stderr!r}")
