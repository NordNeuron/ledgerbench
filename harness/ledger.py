"""Ledger load/append/replay for Arm B, plus shared task-def / LEDGER-META
parsing and a pytest-file-runner used by both arms.py and oracle.py.
"""
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from harness import config


def parse_meta(assertion_path: Path) -> dict:
    with open(assertion_path, encoding="utf-8") as f:
        lines = f.readlines()[:10]
    if not lines or lines[0].strip() != "# LEDGER-META":
        raise ValueError(f"{assertion_path} missing '# LEDGER-META' header")

    meta = {}
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped.startswith("#"):
            break
        content = stripped[1:].strip()
        if not content or ":" not in content:
            continue
        key, _, value = content.partition(":")
        key = key.strip()
        value = value.strip()
        meta[key] = yaml.safe_load(value) if key == "assumes" else value

    required = {"id", "requirement", "introduced_task", "assumes", "tier"}
    missing = required - meta.keys()
    if missing:
        raise ValueError(f"{assertion_path} LEDGER-META missing fields: {sorted(missing)}")
    return meta


def load_task_def(task_id: str) -> dict:
    path = config.TASK_DEFS_DIR / f"{task_id}.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_task_defs():
    return [load_task_def(tid) for tid in config.TASK_IDS]


def classname_for_file(path: Path) -> str:
    """The dotted classname pytest's JUnit report uses for a bare test
    function in this file, given ROOT_DIR as pytest's rootdir/cwd."""
    rel = Path(path).resolve().relative_to(config.ROOT_DIR)
    return ".".join(rel.with_suffix("").parts)


def run_pytest_files(files, workspace: Path, extra_env: dict | None = None):
    """Run pytest over the given assertion/oracle files against `workspace`
    (communicated via config.WORKSPACE_ENV_VAR). Returns (passed, failing_tests)
    where failing_tests is a list of "classname::name" strings."""
    if not files:
        return True, []

    fd, junit_path = tempfile.mkstemp(suffix=".xml")
    os.close(fd)
    try:
        env = dict(os.environ)
        env[config.WORKSPACE_ENV_VAR] = str(workspace)
        if extra_env:
            env.update(extra_env)
        args = [
            sys.executable, "-m", "pytest", "-q", "--tb=short",
            "-p", "no:cacheprovider",
            f"--junitxml={junit_path}",
            *[str(f) for f in files],
        ]
        result = subprocess.run(
            args, capture_output=True, text=True, env=env, cwd=config.ROOT_DIR
        )

        failing_tests = []
        try:
            tree = ET.parse(junit_path)
            for testcase in tree.getroot().iter("testcase"):
                if testcase.find("failure") is not None or testcase.find("error") is not None:
                    classname = testcase.get("classname", "")
                    name = testcase.get("name", "")
                    failing_tests.append(f"{classname}::{name}")
        except ET.ParseError:
            # pytest crashed before writing a report (e.g. collection error).
            failing_tests = ["<collection error>"] if result.returncode != 0 else []

        passed = result.returncode == 0
        return passed, failing_tests
    finally:
        if os.path.exists(junit_path):
            os.unlink(junit_path)


class Ledger:
    """Append-only ledger of admitted assertion files (Arms B and C).

    Entries are never deleted. In Arm C an entry can be demoted from
    "active" to "superseded" by the governance layer: it leaves active
    replay but stays in the ledger (and in the audit pool) forever. Arm B
    never demotes anything, so for it active == admitted.
    """

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.path = run_dir / "ledger.json"
        self.entries = []
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                self.entries = json.load(f)
        for e in self.entries:
            e.setdefault("status", "active")

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, indent=2)

    def admit_task(self, task_id: str) -> None:
        task_def = load_task_def(task_id)
        for rel_path in task_def.get("assertions", []):
            assertion_path = config.TASK_DEFS_DIR / rel_path
            meta = parse_meta(assertion_path)
            self.entries.append({
                "assertion_file": str(assertion_path),
                "meta": meta,
                "admitted_at_task": task_id,
                "status": "active",
            })
        self._save()

    def supersede(self, assertion_id: str) -> None:
        for e in self.entries:
            if e["meta"]["id"] == assertion_id and e["status"] == "active":
                e["status"] = "superseded"
        self._save()

    def active_entries(self):
        return [e for e in self.entries if e["status"] == "active"]

    def superseded_entries(self):
        return [e for e in self.entries if e["status"] == "superseded"]

    def admitted_files(self):
        return [Path(e["assertion_file"]) for e in self.entries]

    def active_files(self):
        return [Path(e["assertion_file"]) for e in self.active_entries()]

    def replay(self, workspace: Path, extra_files=None):
        """Run the active ledger plus any extra_files against workspace."""
        files = self.active_files() + list(extra_files or [])
        return run_pytest_files(files, workspace)
