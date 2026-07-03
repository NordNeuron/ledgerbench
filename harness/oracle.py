"""Hidden-oracle runner. Harness-only: results are logged but never fed
into any prompt (see BUILD_SPEC.md section 7, isolation rules).

Each call copies the current workspace into a fresh temporary directory
and runs the requested oracle files against that copy, so oracle test
files (which live under oracles/, outside the workspace) never get written
into the git-tracked workspace the model can see.
"""
import tempfile
from pathlib import Path

from harness import config, ledger
from harness import workspace as workspace_mod


def run_oracles(workspace: Path, task_ids: list) -> dict:
    """Returns {task_id: {"pass": bool, "failing_tests": [...]}} for each
    task_id in task_ids, run against a single temp copy of `workspace`.

    All requested oracle files run in one pytest invocation (rather than
    one subprocess per task) and results are bucketed back out by
    classname; this matters because run_oracles is called after every
    iteration for every task attempted so far, so per-task subprocess
    overhead compounds badly over a full run.
    """
    with tempfile.TemporaryDirectory(prefix="ledgerbench_oracle_") as tmp:
        tmp_path = Path(tmp) / "workspace_copy"
        workspace_mod.copy_to_temp(workspace, tmp_path)

        files = [config.ORACLE_DIR / f"{task_id}_oracle.py" for task_id in task_ids]
        overall_passed, failing_tests = ledger.run_pytest_files(files, tmp_path)

        if not overall_passed and failing_tests == ["<collection error>"]:
            # pytest crashed before producing per-test results; treat every
            # requested task as failed rather than silently passing them.
            return {tid: {"pass": False, "failing_tests": ["<collection error>"]} for tid in task_ids}

        results = {}
        for task_id, oracle_file in zip(task_ids, files):
            classname = ledger.classname_for_file(oracle_file)
            prefix = f"{classname}::"
            task_failing = [t for t in failing_tests if t.startswith(prefix)]
            results[task_id] = {"pass": len(task_failing) == 0, "failing_tests": task_failing}
        return results


def all_passed(results: dict) -> bool:
    return all(r["pass"] for r in results.values())


def smoke_probe(workspace: Path) -> bool:
    """Pre-registered broken-window probe: an add -> list round-trip on a
    temp copy of the workspace. Scripted, arm-independent, discretion-free.
    True = the workspace's core CLI functions; False = broken window."""
    import subprocess
    import sys
    with tempfile.TemporaryDirectory(prefix="ledgerbench_smoke_") as tmp:
        tmp_path = Path(tmp) / "workspace_copy"
        workspace_mod.copy_to_temp(workspace, tmp_path)
        for junk in ("tasks.json", "tasks.db", "config.toml"):
            j = tmp_path / junk
            if j.exists():
                j.unlink()
        try:
            add = subprocess.run(
                [sys.executable, "-m", "taskcli", "add", "Smoke probe entry"],
                cwd=tmp_path, capture_output=True, text=True, timeout=60,
            )
            listing = subprocess.run(
                [sys.executable, "-m", "taskcli", "list"],
                cwd=tmp_path, capture_output=True, text=True, timeout=60,
            )
        except (subprocess.TimeoutExpired, OSError):
            return False
        return (add.returncode == 0 and listing.returncode == 0
                and "Smoke probe entry" in listing.stdout)
