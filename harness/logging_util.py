"""JSONL run logging.

One JSON object per line. API-call records always include the complete
prompt string (`prompt_full`) and complete raw response (`response_full`).
Verification records capture task id, iteration, and ledger pass/fail with
failing test names; oracle pass/fail is harness-side only and is written
here but never fed back into any prompt.
"""
import json
import time
from pathlib import Path


class RunLogger:
    def __init__(self, run_dir: Path):
        self.path = run_dir / "log.jsonl"
        self._fh = open(self.path, "a", encoding="utf-8")

    def log(self, record: dict) -> None:
        full_record = {"ts": time.time(), **record}
        self._fh.write(json.dumps(full_record) + "\n")
        self._fh.flush()

    def log_api_call(self, task_id, iteration, prompt_full, response_full, usage=None):
        self.log({
            "event": "api_call",
            "task_id": task_id,
            "iteration": iteration,
            "prompt_full": prompt_full,
            "response_full": response_full,
            "usage": usage or {},
        })

    def log_summary_call(self, session_boundary_after, prompt_full, response_full, usage=None):
        self.log({
            "event": "summary_call",
            "session_boundary_after": session_boundary_after,
            "prompt_full": prompt_full,
            "response_full": response_full,
            "usage": usage or {},
        })

    def log_verification(self, task_id, iteration, arm, ledger_pass, failing_tests):
        self.log({
            "event": "verification",
            "task_id": task_id,
            "iteration": iteration,
            "arm": arm,
            "ledger_pass": ledger_pass,
            "failing_tests": failing_tests,
        })

    def log_oracle(self, task_id, iteration, oracle_pass, per_task_results):
        """Harness-side only. per_task_results: {task_id: {"pass": bool,
        "failing_tests": [...]}} for every task attempted so far."""
        self.log({
            "event": "oracle",
            "task_id": task_id,
            "iteration": iteration,
            "oracle_pass": oracle_pass,
            "per_task_results": per_task_results,
        })

    def log_task_result(self, task_id, verdict, iterations_used):
        self.log({
            "event": "task_result",
            "task_id": task_id,
            "verdict": verdict,
            "iterations_used": iterations_used,
        })

    def log_m4_event(self, task_id, iteration):
        self.log({
            "event": "m4_blocked_valid_solution",
            "task_id": task_id,
            "iteration": iteration,
        })

    def close(self) -> None:
        self._fh.close()


def read_log(run_dir: Path):
    path = run_dir / "log.jsonl"
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
