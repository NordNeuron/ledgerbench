"""CLI entry point for the LedgerBench Phase 0 harness.

    python -m harness.run_pilot --arm A|B --seed N [--dry-run]
"""
import argparse
import time

from harness import agent, arms, config, ledger, oracle
from harness import workspace as workspace_mod
from harness.logging_util import RunLogger


def make_run_id(arm: str, seed: int, dry_run: bool) -> str:
    prefix = "dryrun_" if dry_run else "run_"
    arm_slug = arm.replace("+", "plus")
    return f"{prefix}arm{arm_slug}_seed{seed}_{int(time.time())}"


def run(arm: str, seed: int, dry_run: bool = False):
    run_id = make_run_id(arm, seed, dry_run)
    run_dir = config.RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    workspace = workspace_mod.create_workspace(run_dir)
    logger = RunLogger(run_dir)
    logger.log({
        "event": "run_start", "arm": arm, "seed": seed, "dry_run": dry_run, "run_id": run_id,
        # Exact model string, explicit in every run record: the pilot runs a
        # non-spec model (BUILD_SPEC_2 WP3).
        "model": "dry-run-canned-solver" if dry_run else config.MODEL,
        "base_url": None if dry_run else config.ANTHROPIC_BASE_URL,
        "temperature": config.TEMPERATURE,
        "max_tokens": config.MAX_TOKENS,
    })

    solver = agent.DryRunSolver(logger) if dry_run else agent.RealSolver(logger)
    strategy = arms.get_arm(arm, run_dir, logger, dry_run=dry_run)

    task_defs = ledger.load_all_task_defs()
    all_task_ids = [td["id"] for td in task_defs]

    messages = []
    for index, task_def in enumerate(task_defs):
        task_id = task_def["id"]
        tasks_so_far = all_task_ids[: index + 1]

        # Evidence-triggered amendment happens at task LOAD, before any
        # generator call (spec 4.2) — the system prompt below must already
        # reflect any supersessions.
        strategy.on_task_load(task_def)

        task_prompt = agent.build_task_prompt(task_def)
        messages.append({"role": "user", "content": task_prompt})

        verdict = None
        iteration = 0
        while iteration < config.REPAIR_BUDGET:
            iteration += 1
            # Rebuilt each iteration: a mid-task supersession (Arm D lobby,
            # C+ docket) must leave the very next generator prompt, or the
            # separation invariant breaks.
            system_prompt = strategy.build_system_prompt(task_id)
            response_text = solver.call(system_prompt, messages, task_id, iteration)
            messages.append({"role": "assistant", "content": response_text})

            blocks = agent.parse_file_blocks(response_text)
            if not blocks:
                messages.append({"role": "user", "content": agent.build_parse_failure_message()})
                continue

            agent.write_file_blocks(workspace, blocks)
            workspace_mod.commit(workspace, f"{task_id} iter{iteration}")

            strategy.on_response(response_text, task_def)

            passed, failing_tests = strategy.verify(workspace, task_def)
            logger.log_verification(task_id, iteration, strategy.name, passed, failing_tests)

            oracle_results = oracle.run_oracles(workspace, tasks_so_far)
            oracle_pass = oracle.all_passed(oracle_results)
            logger.log_oracle(task_id, iteration, oracle_pass, oracle_results)

            if strategy.name in ("B", "C", "C+", "D") and oracle_pass and not passed:
                logger.log_m4_event(task_id, iteration)

            if passed:
                verdict = "PASS"
                break
            if iteration < config.REPAIR_BUDGET:
                messages.append({"role": "user", "content": agent.build_repair_message(failing_tests)})
            else:
                verdict = "FAILED"

        if verdict is None:
            verdict = "FAILED"
        logger.log_task_result(task_id, verdict, iteration)

        # Broken-window smoke probe (pre-registered analysis rule): a
        # scripted add->list round-trip against the task's final workspace
        # state, identical across arms, zero analyst discretion. H1 events
        # at smoke-failed tasks are excluded; post-recovery persisting
        # failures count as genuine.
        smoke_ok = oracle.smoke_probe(workspace)
        logger.log({"event": "smoke_probe", "task_id": task_id, "ok": smoke_ok})

        strategy.on_task_concluded(task_id, verdict, workspace=workspace)

        if task_id in config.SESSION_BOUNDARY_AFTER:
            strategy.on_session_boundary(workspace)
            if strategy.needs_summary_call():
                messages.append({
                    "role": "user",
                    "content": "Summarize the requirements and decisions so far in <=1500 tokens.",
                })
                summary_text = solver.call_summary(system_prompt, messages, task_id)
                strategy.apply_summary(summary_text)
            messages = []

    logger.log({"event": "run_end", "run_id": run_id})
    logger.close()
    return run_dir


def main():
    parser = argparse.ArgumentParser(description="Run one LedgerBench Phase 0 pilot arm.")
    parser.add_argument("--arm", required=True, choices=["A", "B", "C", "C+", "D"])
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_dir = run(args.arm, args.seed, dry_run=args.dry_run)
    print(f"Run complete: {run_dir}")


if __name__ == "__main__":
    main()
