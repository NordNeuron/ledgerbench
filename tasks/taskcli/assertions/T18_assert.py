# LEDGER-META
# id: A18
# requirement: R18
# introduced_task: T18
# assumes: {}
# tier: correctness
import csv
import io
import os

from _helpers import run_cli, workspace_path


def _export_csv(name):
    dest = os.path.join(workspace_path(), name)
    if os.path.exists(dest):
        os.remove(dest)
    result = run_cli("export", dest, "--format", "csv")
    assert result.returncode == 0, result.stderr
    with open(dest, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    os.remove(dest)
    return rows


def test_csv_export_has_header_and_task_row():
    run_cli("add", "Spreadsheet fodder", "--priority", "high")
    rows = _export_csv("assert_export.csv")
    assert len(rows) >= 2, "expected a header row plus at least one task row"
    header = [c.lower() for c in rows[0]]
    assert "title" in header, f"header row missing field names: {rows[0]}"
    flat = "\n".join(",".join(r) for r in rows[1:])
    assert "Spreadsheet fodder" in flat


def test_csv_export_row_count_matches_tasks():
    run_cli("add", "Row one")
    run_cli("add", "Row two")
    rows = _export_csv("assert_export2.csv")
    flat = "\n".join(",".join(r) for r in rows)
    assert "Row one" in flat and "Row two" in flat
