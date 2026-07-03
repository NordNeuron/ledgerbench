"""Git-tracked project copy management.

Each run gets its own workspace directory, seeded from projects/taskcli/
and tracked with git so every accepted model diff becomes a commit.
"""
import shutil
import subprocess
from pathlib import Path

from harness import config


def _run_git(args, cwd):
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {cwd}:\n{result.stdout}\n{result.stderr}"
        )
    return result


def create_workspace(run_dir: Path) -> Path:
    """Copy projects/taskcli/ into run_dir/workspace, git init, commit as seed."""
    workspace = run_dir / "workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    shutil.copytree(config.SEED_PROJECT_DIR, workspace)

    _run_git(["init", "-q"], cwd=workspace)
    _run_git(["config", "user.email", "ledgerbench@example.com"], cwd=workspace)
    _run_git(["config", "user.name", "LedgerBench"], cwd=workspace)
    _run_git(["add", "-A"], cwd=workspace)
    _run_git(["commit", "-q", "-m", "seed"], cwd=workspace)
    return workspace


def commit(workspace: Path, message: str) -> None:
    _run_git(["add", "-A"], cwd=workspace)
    # Nothing to commit is not an error (e.g. a repair that changes nothing).
    result = subprocess.run(
        ["git", "commit", "-q", "-m", message],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and "nothing to commit" not in (result.stdout + result.stderr):
        raise RuntimeError(f"git commit failed in {workspace}:\n{result.stdout}\n{result.stderr}")


def copy_to_temp(workspace: Path, dest: Path) -> Path:
    """Copy a workspace (excluding .git) to an arbitrary destination directory."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(workspace, dest, ignore=shutil.ignore_patterns(".git"))
    return dest
