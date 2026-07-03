# LEDGER-META
# id: A9
# requirement: R9
# introduced_task: T9
# assumes: {}
# tier: prohibition
from _helpers import extract_id, run_cli


def test_add_prints_exactly_the_id():
    result = run_cli("add", "Quiet entry")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().isdigit(), f"add printed more than the id: {result.stdout!r}"
    assert result.stderr == "", f"add wrote to stderr on success: {result.stderr!r}"


def test_done_success_is_completely_silent():
    run_cli("add", "Silence me")
    line = next(l for l in run_cli("list").stdout.splitlines() if "Silence me" in l)
    result = run_cli("done", extract_id(line))
    assert result.returncode == 0, result.stderr
    assert result.stdout == "", f"done printed on success: {result.stdout!r}"
    assert result.stderr == "", f"done wrote stderr on success: {result.stderr!r}"


def test_delete_success_is_completely_silent():
    run_cli("add", "Remove me")
    line = next(l for l in run_cli("list").stdout.splitlines() if "Remove me" in l)
    result = run_cli("delete", extract_id(line))
    assert result.returncode == 0, result.stderr
    assert result.stdout == "" and result.stderr == "", (
        f"delete printed on success: out={result.stdout!r} err={result.stderr!r}")
