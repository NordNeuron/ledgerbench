from _helpers import extract_id, run_cli


def test_tags_survive_task_lifecycle():
    run_cli("add", "Tagged journey", "--tag", "quest")
    line = next(l for l in run_cli("list").stdout.splitlines() if "Tagged journey" in l)
    run_cli("done", extract_id(line))
    result = run_cli("list", "--tag", "quest")
    assert result.returncode == 0, result.stderr
    assert "Tagged journey" in result.stdout, "tag lost after done"


def test_tag_filter_empty_when_no_match():
    run_cli("add", "Plain as bread")
    result = run_cli("list", "--tag", "nonexistent")
    assert result.returncode == 0, result.stderr
    assert "Plain as bread" not in result.stdout
