import json
import os

from _helpers import extract_id, run_cli, workspace_path


def _read_export(dest):
    """Regime-agnostic export reader (TRAP_DESIGN 6.3): accepts a JSON
    array (pre-T14 format regime) or JSON Lines, or any text containing the
    task objects — the oracle checks WHAT is exported, not how it is laid
    out."""
    with open(dest, encoding="utf-8") as f:
        text = f.read().strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        return [data]
    except json.JSONDecodeError:
        rows = []
        for line in text.splitlines():
            line = line.strip().rstrip(",")
            if not line or line in ("[", "]"):
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows


def test_export_contains_added_task():
    run_cli("add", "Snapshot entry", "--priority", "low")
    dest = os.path.join(workspace_path(), "oracle_export.json")
    result = run_cli("export", dest)
    assert result.returncode == 0, result.stderr
    rows = _read_export(dest)
    os.remove(dest)
    assert any(r.get("title") == "Snapshot entry" for r in rows)


def test_export_keeps_archived_tasks():
    # Regression detector (TRAP_DESIGN 6.5): the exact violation of a later
    # list/export unification is inheriting list's archived-exclusion.
    run_cli("add", "Buried treasure")
    line = next(l for l in run_cli("list").stdout.splitlines() if "Buried treasure" in l)
    run_cli("done", extract_id(line))
    run_cli("archive")
    listed = run_cli("list").stdout
    assert "Buried treasure" not in listed, "archive should hide from default list"

    dest = os.path.join(workspace_path(), "oracle_export_arch.json")
    result = run_cli("export", dest)
    assert result.returncode == 0, result.stderr
    rows = _read_export(dest)
    os.remove(dest)
    assert any(r.get("title") == "Buried treasure" for r in rows), (
        "archived task lost from export - unification-style regression")
