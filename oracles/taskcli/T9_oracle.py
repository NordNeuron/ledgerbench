from _helpers import extract_id, run_cli


def test_done_prints_nothing_on_success():
    run_cli("add", "Hush task")
    line = next(l for l in run_cli("list").stdout.splitlines() if "Hush task" in l)
    result = run_cli("done", extract_id(line))
    assert result.returncode == 0
    assert result.stdout == "" and result.stderr == ""


def test_mutating_commands_stay_silent_end_to_end():
    # Regression detector (TRAP_DESIGN 6.5): the exact violation a later
    # "friendly feedback" pass introduces is confirmation chatter on
    # add/done/delete. Probe all three in one flow.
    add_result = run_cli("add", "Pipeline entry")
    assert add_result.stdout.strip().isdigit(), (
        f"add output not a bare id: {add_result.stdout!r}")
    task_id = add_result.stdout.strip()
    done_result = run_cli("done", task_id)
    delete_result = run_cli("delete", task_id)
    assert done_result.stdout == "" and done_result.stderr == "", (
        f"done chatter: {done_result.stdout!r} {done_result.stderr!r}")
    assert delete_result.stdout == "" and delete_result.stderr == "", (
        f"delete chatter: {delete_result.stdout!r} {delete_result.stderr!r}")
