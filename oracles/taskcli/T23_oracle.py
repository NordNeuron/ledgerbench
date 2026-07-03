import os

from _helpers import extract_id, run_cli, workspace_path


def test_unified_path_keeps_archived_in_export():
    # Trap-task oracle (M1 channel): the exact violation is the unified
    # query inheriting list's archived-exclusion, silently shrinking
    # exports.
    run_cli("add", "Deep archive entry")
    line = next(l for l in run_cli("list").stdout.splitlines()
                if "Deep archive entry" in l)
    run_cli("done", extract_id(line))
    run_cli("archive")
    assert "Deep archive entry" not in run_cli("list").stdout

    dest = os.path.join(workspace_path(), "oracle_unified.out")
    result = run_cli("export", dest)
    assert result.returncode == 0, result.stderr
    with open(dest, encoding="utf-8") as f:
        content = f.read()
    os.remove(dest)
    assert "Deep archive entry" in content, (
        "unified query path dropped archived tasks from export")


def test_unified_path_keeps_tag_filter_working():
    run_cli("add", "Tag checkpoint", "--tag", "refactor")
    result = run_cli("list", "--tag", "refactor")
    assert result.returncode == 0, result.stderr
    assert "Tag checkpoint" in result.stdout
