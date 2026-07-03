"""Offline oracle re-scorer (BUILD_SPEC_2 WP1/WP2).

Replays the (current, possibly fixed) hidden oracles against every
per-iteration workspace state preserved in a run's git history, without any
model calls, and writes the results to runs/<id>/rescore.json. analyze.py
prefers rescore.json over the log's live oracle events when it exists, so
runs scored with a buggy oracle can be re-scored after the oracle is fixed.

    python -m harness.rescore runs/run_armA_seed1_XXX [runs/...]
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from harness import config, oracle
from harness.logging_util import read_log


def _commit_list(workspace: Path) -> list:
    """[(message, hash)] in chronological order."""
    out = subprocess.run(
        ["git", "log", "--reverse", "--format=%H %s"],
        cwd=workspace, capture_output=True, text=True, check=True,
    ).stdout
    commits = []
    for line in out.strip().splitlines():
        sha, _, msg = line.partition(" ")
        commits.append((msg, sha))
    return commits


def rescore_run(run_dir: Path) -> dict:
    workspace = run_dir / "workspace"
    records = read_log(run_dir)
    commits = _commit_list(workspace)

    # Logged iterations, in order. Each corresponds to the workspace state
    # after that iteration's diff was applied; an iteration whose diff was
    # empty has no commit of its own, so it inherits the previous state.
    iterations = [
        (r["task_id"], r["iteration"]) for r in records if r.get("event") == "verification"
    ]

    with tempfile.TemporaryDirectory(prefix="ledgerbench_rescore_") as tmp:
        clone = Path(tmp) / "clone"
        subprocess.run(
            ["git", "clone", "-q", str(workspace), str(clone)],
            capture_output=True, text=True, check=True,
        )

        results = []
        commit_idx = 0  # points at the commit currently checked out conceptually
        for task_id, iteration in iterations:
            expected_msg = f"{task_id} iter{iteration}"
            if commit_idx + 1 < len(commits) and commits[commit_idx + 1][0] == expected_msg:
                commit_idx += 1
            msg, sha = commits[commit_idx]
            subprocess.run(
                ["git", "checkout", "-q", "--force", sha],
                cwd=clone, capture_output=True, text=True, check=True,
            )
            # Untracked files from previous checkouts/test runs (tasks.json,
            # tasks.db, __pycache__) would leak state between iterations.
            subprocess.run(
                ["git", "clean", "-qfdx"],
                cwd=clone, capture_output=True, text=True, check=True,
            )

            task_num = config.TASK_IDS.index(task_id) + 1
            task_ids_so_far = config.TASK_IDS[:task_num]
            per_task = oracle.run_oracles(clone, task_ids_so_far)
            results.append({
                "task_id": task_id,
                "iteration": iteration,
                "commit": sha,
                "commit_message": msg,
                "oracle_pass": oracle.all_passed(per_task),
                "per_task_results": per_task,
            })
            print(f"  {task_id} iter{iteration} @ {sha[:8]} ({msg!r}): "
                  f"{'ALL PASS' if oracle.all_passed(per_task) else 'failures'}")

    return {"run_dir": str(run_dir), "oracle_events": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", help="Run directories to re-score.")
    args = parser.parse_args()
    for run_dir in args.runs:
        run_dir = Path(run_dir)
        print(f"Re-scoring {run_dir} ...")
        data = rescore_run(run_dir)
        out = run_dir / "rescore.json"
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
