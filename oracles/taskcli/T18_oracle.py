import os

from _helpers import extract_id, run_cli, workspace_path


def test_csv_export_includes_archived_tasks():
    # Cross-feature probe: R13 (exports are complete snapshots) applies to
    # every export format, and the CSV path is a fresh rewrite of the
    # file-writing code (TRAP_DESIGN P7 rewrite bait).
    run_cli("add", "Filed away")
    line = next(l for l in run_cli("list").stdout.splitlines() if "Filed away" in l)
    run_cli("done", extract_id(line))
    run_cli("archive")
    dest = os.path.join(workspace_path(), "oracle_export.csv")
    result = run_cli("export", dest, "--format", "csv")
    assert result.returncode == 0, result.stderr
    with open(dest, encoding="utf-8") as f:
        content = f.read()
    os.remove(dest)
    assert "Filed away" in content, "archived task missing from CSV export"


def test_csv_export_openable_and_headered():
    run_cli("add", "Header check")
    dest = os.path.join(workspace_path(), "oracle_export2.csv")
    assert run_cli("export", dest, "--format", "csv").returncode == 0
    with open(dest, encoding="utf-8") as f:
        first_line = f.readline().lower()
    os.remove(dest)
    assert "title" in first_line, f"no header row: {first_line!r}"
