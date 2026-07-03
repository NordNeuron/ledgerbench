from _helpers import extract_id, run_cli


def test_compact_never_renumbers_surviving_tasks():
    run_cli("add", "Anchor one")
    run_cli("add", "Doomed middle")
    run_cli("add", "Anchor two")
    lines = run_cli("list").stdout.splitlines()
    id_one = extract_id(next(l for l in lines if "Anchor one" in l))
    id_mid = extract_id(next(l for l in lines if "Doomed middle" in l))
    id_two = extract_id(next(l for l in lines if "Anchor two" in l))

    run_cli("delete", id_mid)
    assert run_cli("compact").returncode == 0
    after = run_cli("list").stdout.splitlines()
    assert extract_id(next(l for l in after if "Anchor one" in l)) == id_one, (
        "compact renumbered a surviving task")
    assert extract_id(next(l for l in after if "Anchor two" in l)) == id_two, (
        "compact renumbered a surviving task")


def test_old_id_still_addresses_same_task_after_compact():
    run_cli("add", "Stable target")
    add_result = run_cli("add", "Sacrifice")
    run_cli("delete", add_result.stdout.strip())
    lines = run_cli("list").stdout.splitlines()
    target_id = extract_id(next(l for l in lines if "Stable target" in l))
    run_cli("compact")
    result = run_cli("done", target_id)
    assert result.returncode == 0, (
        f"pre-compact id no longer addresses its task: {result.stderr!r}")
    after = run_cli("list").stdout.splitlines()
    target_line = next(l for l in after if "Stable target" in l)
    assert extract_id(target_line) == target_id
