# LEDGER-META
# id: A13
# requirement: R13
# introduced_task: T13
# assumes: {export_format: json_array}
# tier: correctness
import json
import os

from _helpers import extract_id, run_cli, workspace_path


def _export(name):
    dest = os.path.join(workspace_path(), name)
    if os.path.exists(dest):
        os.remove(dest)
    result = run_cli("export", dest)
    assert result.returncode == 0, result.stderr
    with open(dest, encoding="utf-8") as f:
        data = json.load(f)
    os.remove(dest)
    assert isinstance(data, list), "export must be a JSON array"
    return data


def test_export_is_json_array_with_task_fields():
    run_cli("add", "Exported item", "--priority", "high", "--due", "2026-09-01")
    data = _export("assert_export.json")
    task = next(t for t in data if t.get("title") == "Exported item")
    assert task.get("priority") == "high"
    assert "2026-09-01" in str(task.get("due", "")) or "2026-09-01" in json.dumps(task)


def test_export_includes_archived_tasks():
    run_cli("add", "Archived export target")
    line = next(l for l in run_cli("list").stdout.splitlines()
                if "Archived export target" in l)
    run_cli("done", extract_id(line))
    run_cli("archive")
    data = _export("assert_export_arch.json")
    assert any(t.get("title") == "Archived export target" for t in data), (
        "archived task missing from export")
