# LEDGER-META
# id: A23
# requirement: R23
# introduced_task: T23
# assumes: {}
# tier: correctness
# Deliberately silent about archived tasks in exports (TRAP_DESIGN P5):
# that invariant is guarded by A13 in the ledger and the T13 oracle
# detector. This file only smoke-checks the refactor.
import os

from _helpers import run_cli, workspace_path


def test_list_still_works_after_refactor():
    run_cli("add", "Refactor survivor", "--priority", "med")
    result = run_cli("list")
    assert result.returncode == 0, result.stderr
    assert "Refactor survivor" in result.stdout


def test_export_still_works_after_refactor():
    run_cli("add", "Exportable entry")
    dest = os.path.join(workspace_path(), "refactor_export.out")
    result = run_cli("export", dest)
    assert result.returncode == 0, result.stderr
    with open(dest, encoding="utf-8") as f:
        content = f.read()
    os.remove(dest)
    assert "Exportable entry" in content
