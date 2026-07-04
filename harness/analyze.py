"""Metrics and plots from run logs, plus the hidden-oracle leak checker.

    python -m harness.analyze                     # analyze all runs/, write results/
    python -m harness.analyze --runs runs/foo ...  # analyze specific run dirs
    python -m harness.analyze --leak-check runs/foo
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from harness import config
from harness.logging_util import read_log


def _oracle_events(run_dir: Path, records: list) -> list:
    """Per-iteration oracle results. Prefers runs/<id>/rescore.json (offline
    replay against the current oracles, see rescore.py) over the log's live
    oracle events, so runs scored with a since-fixed oracle bug are
    re-scored without re-running the model."""
    rescore_path = run_dir / "rescore.json"
    if rescore_path.exists():
        return json.loads(rescore_path.read_text(encoding="utf-8"))["oracle_events"]
    return [r for r in records if r.get("event") == "oracle"]


def compute_metrics_for_run(run_dir: Path) -> dict:
    records = read_log(run_dir)
    start = next(r for r in records if r.get("event") == "run_start")
    arm, seed = start["arm"], start["seed"]

    # Task set comes from the log, not config: a pilot (8-task) run analyzed
    # under the Phase 1 (24-task) config must not grow phantom rows.
    attempted = {r["task_id"] for r in records if r.get("event") == "task_result"}
    task_order = [tid for tid in config.TASK_IDS if tid in attempted] or config.TASK_IDS

    oracle_events = _oracle_events(run_dir, records)

    last_oracle_snapshot = {}
    for r in oracle_events:
        last_oracle_snapshot[r["task_id"]] = r["per_task_results"]

    m1_per_task = {}
    m1_cumulative = {}
    m2_regression_count_per_task = {}
    prev_passing = set()
    cumulative_so_far = 0.0
    for idx, tid in enumerate(task_order):
        considered = set(task_order[: idx + 1])
        snapshot = last_oracle_snapshot.get(tid)
        if snapshot is None:
            m1_per_task[tid] = False
            m1_cumulative[tid] = cumulative_so_far
            m2_regression_count_per_task[tid] = 0
            continue
        passing_now = {t for t, res in snapshot.items() if res.get("pass")}
        m1_per_task[tid] = tid in passing_now
        cumulative_so_far = len(passing_now & considered) / len(considered)
        m1_cumulative[tid] = cumulative_so_far
        m2_regression_count_per_task[tid] = len(prev_passing - passing_now)
        prev_passing = passing_now

    session_ends = set(config.SESSION_BOUNDARY_AFTER) | ({task_order[-1]} if task_order else set())
    m3_session_end = {
        tid: m1_cumulative[tid] for tid in task_order
        if tid in session_ends and tid in m1_cumulative
    }

    # M4 variants, recomputed from per-iteration oracle + ledger results
    # rather than trusting logged m4 events (which reflect whatever oracle
    # version was live during the run).
    #   strict: ALL oracles so far pass, ledger replay fails.
    #   local:  (a) the current task's own oracle passes, (b) no oracle test
    #           that passed on the previous task's final state newly fails,
    #           (c) ledger replay fails. Robust to a single permanent oracle
    #           failure earlier in the run, which disables strict entirely.
    ledger_pass_by_iter = {
        (r["task_id"], r["iteration"]): r["ledger_pass"]
        for r in records if r.get("event") == "verification"
    }
    m4_strict_per_task = {tid: 0 for tid in task_order}
    m4_local_per_task = {tid: 0 for tid in task_order}
    m4_local_iterations = []
    # M4 is defined only for ledgered arms (B, C): Arm A's verification is
    # just the current task's reference assertions, not a ledger replay, so
    # M4 = 0 structurally (Phase 0 spec section 8).
    for r in (oracle_events if arm != "A" else []):
        tid, iteration = r["task_id"], r["iteration"]
        ledger_pass = ledger_pass_by_iter.get((tid, iteration))
        if ledger_pass is not False:
            continue  # ledger passed (or unknown): neither variant can fire
        per_task = r["per_task_results"]
        if all(res["pass"] for res in per_task.values()):
            m4_strict_per_task[tid] += 1
        own_pass = per_task.get(tid, {}).get("pass", False)
        idx = task_order.index(tid)
        prev_final = last_oracle_snapshot.get(task_order[idx - 1], {}) if idx > 0 else {}
        newly_failed = []
        for prior_tid, res in per_task.items():
            if prior_tid == tid:
                continue
            prev_failing = set(prev_final.get(prior_tid, {}).get("failing_tests", []))
            newly_failed.extend(set(res["failing_tests"]) - prev_failing)
        if own_pass and not newly_failed:
            m4_local_per_task[tid] += 1
            m4_local_iterations.append({"task_id": tid, "iteration": iteration})

    tokens_in = tokens_out = 0
    tokens_in_task = {tid: 0 for tid in task_order}
    tokens_out_task = {tid: 0 for tid in task_order}
    for r in records:
        if r.get("event") in ("api_call", "summary_call"):
            usage = r.get("usage") or {}
            tokens_in += usage.get("input_tokens", 0)
            tokens_out += usage.get("output_tokens", 0)
            tid = r.get("task_id")
            if r.get("event") == "api_call" and tid in tokens_in_task:
                tokens_in_task[tid] += usage.get("input_tokens", 0)
                tokens_out_task[tid] += usage.get("output_tokens", 0)

    iterations_used = [r["iterations_used"] for r in records if r.get("event") == "task_result"]
    m8_mean_repair_iterations = sum(iterations_used) / len(iterations_used) if iterations_used else 0.0

    # The arm's own verdict, as distinct from the oracle's (M1). Where these
    # diverge — oracle PASS but arm FAILED — the arm's verification rejected
    # work that was actually correct.
    arm_verdict = {
        r["task_id"]: r["verdict"] for r in records if r.get("event") == "task_result"
    }

    # Vestigial-code events (TRAP_DESIGN section 5, T20): after the
    # merely-obsolete config regime change, code still reading the
    # deprecated TASKCLI_TODAY env var is dead-regime code kept alive
    # (typically to satisfy stale env-var assertions). Count, per post-T20
    # task, whether its final commit still greps for the env var.
    vestigial_per_task = {}
    workspace = run_dir / "workspace"
    if "T20" in task_order and workspace.exists():
        import subprocess
        log_out = subprocess.run(
            ["git", "log", "--reverse", "--format=%H %s"],
            cwd=workspace, capture_output=True, text=True,
        ).stdout
        final_commit = {}
        for line in log_out.strip().splitlines():
            sha, _, msg = line.partition(" ")
            for tid in task_order:
                if msg.startswith(f"{tid} iter"):
                    final_commit[tid] = sha
        post_t20 = task_order[task_order.index("T20"):]
        for tid in post_t20:
            sha = final_commit.get(tid)
            if not sha:
                continue
            grep = subprocess.run(
                ["git", "grep", "-q", "TASKCLI_TODAY", sha],
                cwd=workspace, capture_output=True, text=True,
            )
            vestigial_per_task[tid] = grep.returncode == 0

    # M6: judge decisions (Arm C governance activity; zero elsewhere).
    m6 = {"supersede": 0, "retain": 0, "conflict_unresolved": 0}
    for r in records:
        if r.get("event") == "judge_call":
            m6["supersede" if r["verdict"] == "SUPERSEDE" else "retain"] += 1
        elif r.get("event") == "conflict_unresolved":
            m6["conflict_unresolved"] += 1

    return {
        "arm_verdict": arm_verdict,
        "task_order": task_order,
        "run_dir": str(run_dir),
        "arm": arm,
        "seed": seed,
        "m1_per_task": m1_per_task,
        "m1_cumulative": m1_cumulative,
        "m2_regression_count_per_task": m2_regression_count_per_task,
        "m3_session_end": m3_session_end,
        "m4_strict_per_task": m4_strict_per_task,
        "m4_local_per_task": m4_local_per_task,
        "m4_local_iterations": m4_local_iterations,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_in_task": tokens_in_task,
        "tokens_out_task": tokens_out_task,
        "m8_mean_repair_iterations": m8_mean_repair_iterations,
        "m6": m6,
        "vestigial_per_task": vestigial_per_task,
        "rescored": (run_dir / "rescore.json").exists(),
    }


def write_metrics_csv(all_metrics, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "run_dir", "arm", "seed", "task_id", "arm_verdict", "m1_pass", "m1_cumulative",
            "m2_regression_count", "m3_session_retention",
            "m4_strict_count", "m4_local_count",
            "tokens_in_task", "tokens_out_task",
            "tokens_in_total", "tokens_out_total", "mean_repair_iterations",
            "m6_supersede", "m6_retain", "m6_conflict_unresolved",
            "vestigial_code", "rescored",
        ])
        for m in all_metrics:
            for tid in m.get("task_order", config.TASK_IDS):
                m3 = m["m3_session_end"].get(tid, "")
                writer.writerow([
                    m["run_dir"], m["arm"], m["seed"], tid,
                    m["arm_verdict"].get(tid, ""),
                    m["m1_per_task"].get(tid, False),
                    round(m["m1_cumulative"].get(tid, 0.0), 4),
                    m["m2_regression_count_per_task"].get(tid, 0),
                    round(m3, 4) if m3 != "" else "",
                    m["m4_strict_per_task"].get(tid, 0),
                    m["m4_local_per_task"].get(tid, 0),
                    m["tokens_in_task"].get(tid, 0),
                    m["tokens_out_task"].get(tid, 0),
                    m["tokens_in"], m["tokens_out"],
                    round(m["m8_mean_repair_iterations"], 3),
                    m["m6"]["supersede"], m["m6"]["retain"], m["m6"]["conflict_unresolved"],
                    m["vestigial_per_task"].get(tid, ""),
                    m["rescored"],
                ])


def plot_cumulative_m1(all_metrics, out_path: Path) -> None:
    fig, ax = plt.subplots()
    by_arm = {}
    for m in all_metrics:
        by_arm.setdefault(m["arm"], []).append(m)
    for arm in sorted(by_arm):
        runs = by_arm[arm]
        avg = []
        for tid in config.TASK_IDS:
            vals = [r["m1_cumulative"].get(tid, 0.0) for r in runs]
            avg.append(sum(vals) / len(vals) if vals else 0.0)
        ax.plot(config.TASK_IDS, avg, marker="o", label=f"Arm {arm}")
    ax.set_xlabel("Task")
    ax.set_ylabel("Cumulative M1 (fraction of tasks-so-far passing oracle)")
    ax.set_title("Cumulative task success (M1) per task per arm\n(real runs, rescored oracles)")
    ax.set_ylim(0, 1.05)
    ax.legend()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)


def _annotate_m4_causes(ax, x_by_tid: dict, totals: dict) -> None:
    """T5's M4 events are caused by the reference-assertion extract_id
    defect (see DIAGNOSTICS.md), not by staleness; T6's are the genuine
    regime-change phenomenon. Distinguish them on the chart."""
    notes = {"T5": "assertion-defect\nartifact", "T6": "regime-change\nstaleness"}
    for tid, note in notes.items():
        if totals.get(tid, 0) > 0:
            ax.annotate(
                note, xy=(x_by_tid[tid], totals[tid]),
                xytext=(0, 4), textcoords="offset points",
                ha="center", va="bottom", fontsize=7, style="italic",
            )


def plot_m4_counts(all_metrics, out_path: Path) -> None:
    fig, ax = plt.subplots()
    totals = {tid: 0 for tid in config.TASK_IDS}
    for m in all_metrics:
        if m["arm"] != "B":
            continue
        for tid, count in m["m4_strict_per_task"].items():
            totals[tid] += count
    ax.bar(config.TASK_IDS, [totals[tid] for tid in config.TASK_IDS])
    _annotate_m4_causes(ax, {tid: i for i, tid in enumerate(config.TASK_IDS)}, totals)
    ax.set_xlabel("Task")
    ax.set_ylabel("M4-strict event count (summed across Arm B runs)")
    ax.set_title("Blocked-valid-solution events (M4-strict) per task, Arm B\n(real runs, rescored oracles)")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)


def plot_m4_local_counts(all_metrics, out_path: Path) -> None:
    """Grouped bars per arm (ledgered arms only: A has no ledger replay,
    so M4-local is structurally 0 there)."""
    fig, ax = plt.subplots()
    by_arm = {}
    for m in all_metrics:
        if m["arm"] == "A":
            continue
        totals = by_arm.setdefault(m["arm"], {tid: 0 for tid in config.TASK_IDS})
        for tid, count in m["m4_local_per_task"].items():
            totals[tid] += count
    arms = sorted(by_arm)
    n = max(len(arms), 1)
    width = 0.8 / n
    xs = range(len(config.TASK_IDS))
    for i, arm in enumerate(arms):
        offsets = [x - 0.4 + width * (i + 0.5) for x in xs]
        ax.bar(offsets, [by_arm[arm][tid] for tid in config.TASK_IDS],
               width=width, label=f"Arm {arm}")
    ax.set_xticks(list(xs))
    ax.set_xticklabels(config.TASK_IDS)
    combined = {tid: max(by_arm[a][tid] for a in arms) for tid in config.TASK_IDS} if arms else {}
    _annotate_m4_causes(ax, {tid: i for i, tid in enumerate(config.TASK_IDS)}, combined)
    ax.set_xlabel("Task")
    ax.set_ylabel("M4-local event count (summed across runs)")
    ax.set_title("Blocked-locally-valid-solution events (M4-local) per task\n(real runs, rescored oracles)")
    if arms:
        ax.legend()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)


# H1 detector registry (TRAP_DESIGN + calibration iteration 2, ruling 5):
# each threatened requirement's standing detector tests (living in the
# intro task's oracle file) and its designed trap task. An H1 event is a
# task at whose final state a detector test newly fails (passing at the
# previous task's final state). Channel: "trap" when it happens at the
# designed trap task, "conflict" at T24 (deliberately unsatisfiable, not a
# memory measurement), otherwise "rewrite" (the continuous channel).
# Coercion (ledgered arms regressing under repair pressure) is not
# auto-classified; read the transcript for events in ledgered arms.
H1_DETECTORS = {
    "R2-ids": {"intro": "T2", "trap": "T15", "tests": [
        "test_ids_survive_delete_end_to_end", "test_ids_stable_through_mutations"]},
    "R2-order": {"intro": "T2", "trap": "T17", "tests": [
        "test_default_list_order_is_insertion_order", "test_default_order_not_grouped_by_priority"]},
    "R4-iso": {"intro": "T4", "trap": None, "tests": [
        "test_due_dates_render_iso_wherever_shown"]},
    "R9-silence": {"intro": "T9", "trap": "T19", "tests": [
        "test_done_prints_nothing_on_success", "test_mutating_commands_stay_silent_end_to_end"]},
    # grade "contract": the requirement pins a mechanism; detector failures
    # are contract drift, reported separately from semantic violations
    # (correction-cycle ruling). Default grade is "semantic".
    "R10-atomic": {"intro": "T10", "trap": "T18", "grade": "contract", "tests": [
        "test_backup_stages_through_contracted_tmp_path"]},
    "R11-exitcodes": {"intro": "T11", "trap": "T19", "tests": [
        "test_validation_and_io_errors_use_contracted_codes", "test_exit_codes_survive_error_path_rewrites"]},
    "R12-pipesafety": {"intro": "T12", "trap": "T21", "tests": [
        "test_color_flag_accepted_and_piped_output_clean", "test_no_ansi_anywhere_when_piped"]},
    "R13-archived-export": {"intro": "T13", "trap": "T23", "tests": [
        "test_export_contains_added_task", "test_export_keeps_archived_tasks"]},
}


def _stale_assertion_tests(run_dir: Path, records: list) -> dict:
    """{task_id_threshold: set of classname prefixes}. A test belongs to a
    stale assertion at task T iff its file's `assumes` matches some
    evidence artifact whose introducing task <= T, or the assertion was
    superseded before T (supersessions.jsonl). Used by the pre-registered
    coercion-exclusion rule."""
    from harness import governance, ledger as ledger_mod
    stale_prefix_by_task = {}
    evidences = []
    ev_dir = config.TASK_DEFS_DIR / "evidence"
    if ev_dir.exists():
        for f in sorted(ev_dir.glob("*.md")):
            try:
                evidences.append(governance.parse_evidence(f))
            except ValueError:
                continue
    metas = {}
    for f in sorted(config.ASSERTIONS_DIR.glob("T*_assert.py")) + sorted(config.ASSERTIONS_DIR.glob("T*_*_assert.py")):
        try:
            metas[f] = ledger_mod.parse_meta(f)
        except ValueError:
            continue
    for tid in config.TASK_IDS:
        t_num = int(tid[1:])
        prefixes = set()
        for f, meta in metas.items():
            assumes = meta.get("assumes") or {}
            for ev in evidences:
                inv = ev.get("invalidates") or {}
                ev_num = int(str(ev.get("task", "T99"))[1:])
                if ev_num <= t_num and any(assumes.get(k) == v for k, v in inv.items()):
                    prefixes.add(ledger_mod.classname_for_file(f) + "::")
        stale_prefix_by_task[tid] = prefixes
    return stale_prefix_by_task


def compute_h1_events(oracle_events, task_order, records=None, run_dir=None, arm=None):
    """H1 events under the FROZEN rules: (1) broken-window exclusion — the
    snapshot chain only includes tasks whose smoke probe passed, so
    in-window detector events are skipped and post-recovery persisting
    failures surface at the first healthy task; (2) coercion exclusion —
    in ledgered arms an event is graded channel 'coerced' (excluded from
    H1 counts, kept visible) if the event task's repair feedback contained
    failing stale/superseded assertion tests."""
    records = records or []
    final, smoke = {}, {}
    for r in oracle_events:
        final[r["task_id"]] = r["per_task_results"]
    for r in records:
        if r.get("event") == "smoke_probe":
            smoke[r["task_id"]] = r["ok"]
    # Snapshot chain: smoke-passed tasks only (all tasks when no smoke data
    # exists, e.g. calibration-era runs).
    chain = [t for t in task_order if t in final and smoke.get(t, True)]

    coerced_tasks = set()
    if arm and arm != "A" and run_dir is not None:
        stale_by_task = _stale_assertion_tests(Path(run_dir), records)
        for r in records:
            if r.get("event") != "verification" or r.get("ledger_pass"):
                continue
            tid = r["task_id"]
            prefixes = stale_by_task.get(tid, set())
            if any(t.startswith(p) for t in r.get("failing_tests", []) for p in prefixes):
                coerced_tasks.add(tid)

    events = []
    for req, spec in H1_DETECTORS.items():
        if spec["intro"] not in task_order:
            continue
        intro_idx = task_order.index(spec["intro"])
        for pos, tid in enumerate(chain):
            if task_order.index(tid) <= intro_idx or pos == 0:
                continue
            snap, snap_prev = final[tid], final[chain[pos - 1]]
            def failing(s):
                res = s.get(spec["intro"], {})
                return {t.split("::")[-1] for t in res.get("failing_tests", [])}
            newly = [t for t in spec["tests"]
                     if t in failing(snap) and t not in failing(snap_prev)]
            if newly:
                channel = ("conflict" if tid == "T24"
                           else "coerced" if tid in coerced_tasks
                           else "trap" if tid == spec["trap"] else "rewrite")
                events.append({"requirement": req, "task": tid,
                               "channel": channel, "newly_failed": newly,
                               "grade": spec.get("grade", "semantic")})
    return events


def write_h1_events_csv(all_metrics, run_dirs, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["run_dir", "arm", "seed", "requirement", "task", "channel", "bite_grade", "newly_failed_tests"])
        for m, run_dir in zip(all_metrics, run_dirs):
            records = read_log(run_dir)
            events = compute_h1_events(_oracle_events(run_dir, records), m["task_order"],
                                       records=records, run_dir=run_dir, arm=m["arm"])
            for e in events:
                writer.writerow([m["run_dir"], m["arm"], m["seed"], e["requirement"],
                                 e["task"], e["channel"], e["grade"], ";".join(e["newly_failed"])])


def plot_tokens_per_task(all_metrics, out_path: Path) -> None:
    fig, ax = plt.subplots()
    by_arm = {}
    for m in all_metrics:
        by_arm.setdefault(m["arm"], []).append(m)
    for arm in sorted(by_arm):
        runs = by_arm[arm]
        totals = []
        for tid in config.TASK_IDS:
            vals = [r["tokens_in_task"].get(tid, 0) + r["tokens_out_task"].get(tid, 0)
                    for r in runs]
            totals.append(sum(vals) / len(vals) if vals else 0)
        ax.plot(config.TASK_IDS, totals, marker="o", label=f"Arm {arm}")
    ax.set_xlabel("Task")
    ax.set_ylabel("Mean tokens per task (in + out, generator calls)")
    ax.set_title("Per-task token cost per arm (M7)\n(real runs, rescored oracles)")
    ax.legend()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)


def dump_supersessions(run_dirs, results_dir: Path) -> None:
    for run_dir in run_dirs:
        src = run_dir / "supersessions.jsonl"
        if not src.exists():
            continue
        chain = [json.loads(line) for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
        out = results_dir / f"supersessions_{run_dir.name}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(chain, indent=2), encoding="utf-8")
        print(f"Wrote {out} ({len(chain)} supersession(s))")


SEPARATION_BANNED_STRINGS = ["judge", "supersede", "amendment", "audit pool"]


def separation_check(run_dir: Path) -> int:
    """Spec 4.6, grep-provable separation of powers: generator prompts must
    never contain governance vocabulary, and a superseded assertion's file
    contents must not appear in any generator prompt sent after its
    supersession (before it, the assertion was legitimately active context).
    Scans api_call and summary_call events only — judge_call prompts are the
    judge's own conversation and are exempt by design."""
    records = read_log(run_dir)
    hits = 0

    supersessions = []
    sup_path = run_dir / "supersessions.jsonl"
    if sup_path.exists():
        supersessions = [json.loads(l) for l in sup_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    ledger_path = run_dir / "ledger.json"
    file_by_id = {}
    if ledger_path.exists():
        for e in json.loads(ledger_path.read_text(encoding="utf-8")):
            file_by_id[e["meta"]["id"]] = e["assertion_file"]

    # Chunks shared with OTHER promptable content prove nothing about
    # leakage: assertion files share pytest boilerplate with the active
    # assertions legitimately in the prompt, and ordinary project-code
    # fragments (e.g. "for t in tasks if t") appear in the generator's own
    # committed files, which sit in its conversation because it wrote them.
    # Exclude both corpora; only chunks unique to the superseded file count.
    # Distinctive content (test names, storage-probing asserts) never
    # appears in the CLI implementation, so real leaks still hit.
    import subprocess
    workspace_corpus = ""
    workspace = run_dir / "workspace"
    if workspace.exists():
        workspace_corpus = subprocess.run(
            ["git", "log", "--all", "-p"], cwd=workspace,
            capture_output=True, text=True,
        ).stdout

    superseded_chunks = []  # (assertion_id, chunk, since_ts)
    for s in supersessions:
        path = file_by_id.get(s["assertion_id"])
        if not path:
            continue
        others = []
        for f in sorted(config.TASK_DEFS_DIR.rglob("*")):
            if f.is_file() and f.suffix in (".py", ".yaml", ".yml", ".md") \
                    and f.resolve() != Path(path).resolve():
                others.append(f.read_text(encoding="utf-8"))
        other_corpus = "\n".join(others) + workspace_corpus
        text = Path(path).read_text(encoding="utf-8")
        for i in range(0, max(len(text) - 20, 0) + 1, 20):
            chunk = text[i:i + 20]
            if chunk.strip() and chunk not in other_corpus:
                superseded_chunks.append((s["assertion_id"], chunk, s["timestamp"]))

    for r in records:
        if r.get("event") not in ("api_call", "summary_call"):
            continue
        prompt = r.get("prompt_full") or ""
        lowered = prompt.lower()
        for banned in SEPARATION_BANNED_STRINGS:
            if banned in lowered:
                hits += 1
                print(f"SEPARATION VIOLATION: {banned!r} in generator prompt "
                      f"(task={r.get('task_id')}, iter={r.get('iteration')})")
        # Superseded-content scan is scoped to what the governance layer
        # controls: the system prompt (rebuilt every iteration from the
        # ACTIVE ledger) and the newest user message. In-session
        # conversation HISTORY is immutable by construction — content that
        # entered legitimately pre-supersession (e.g. a failing test name
        # in a T19 repair message, superseded at T20, still visible at
        # T21) is history, not guidance, and cannot be retracted by any
        # implementation. (Check-definition correction, logged in
        # TRAPS.md; the unscoped version was unsatisfiable for any
        # mid-session supersession.)
        try:
            parsed = json.loads(prompt)
            fresh = parsed.get("system", "")
            user_msgs = [m for m in parsed.get("messages", []) if m.get("role") == "user"]
            if user_msgs:
                fresh += "\n" + str(user_msgs[-1].get("content", ""))
        except (json.JSONDecodeError, AttributeError):
            fresh = prompt
        for assertion_id, chunk, since_ts in superseded_chunks:
            if r["ts"] > since_ts and chunk in fresh:
                hits += 1
                print(f"SEPARATION VIOLATION: superseded {assertion_id} content "
                      f"{chunk!r} in fresh generator prompt content after "
                      f"supersession (task={r.get('task_id')}, iter={r.get('iteration')})")
    return hits


def leak_check(run_dir: Path) -> int:
    """Scans every prompt_full in the run's log for (a) any oracle filename
    and (b) 20-char substrings sampled from every file under oracles/.
    Returns the number of hits found (0 = clean).

    Needles that also appear verbatim in tasks/taskcli/ (task prompts and
    reference assertions, which Arm B legitimately includes in full in its
    prompts) are excluded: oracle and assertion test files are written in
    a similar pytest idiom, so generic boilerplate like "from _helpers
    import" or "assert result.returncode ==" coincidentally collides
    between the two without any oracle content ever being read. Only
    needles unique to oracles/ count as a real leak.
    """
    records = read_log(run_dir)

    safe_texts = []
    for f in sorted(config.TASK_DEFS_DIR.rglob("*")):
        if f.is_file() and f.suffix in (".py", ".yaml", ".yml", ".md"):
            safe_texts.append(f.read_text(encoding="utf-8"))
    safe_corpus = "\n".join(safe_texts)

    oracle_files = sorted(config.ORACLES_DIR.rglob("*.py"))
    needles = set()
    for f in oracle_files:
        if f.name not in safe_corpus:
            needles.add(f.name)
        text = f.read_text(encoding="utf-8")
        for i in range(0, max(len(text) - 20, 0) + 1, 20):
            chunk = text[i:i + 20]
            if chunk.strip() and chunk not in safe_corpus:
                needles.add(chunk)

    hits = 0
    for r in records:
        prompt_full = r.get("prompt_full")
        if not prompt_full:
            continue
        for needle in needles:
            if needle in prompt_full:
                hits += 1
                print(
                    f"LEAK: {needle!r} found in prompt_full "
                    f"(event={r.get('event')}, task={r.get('task_id')}, iter={r.get('iteration')})"
                )
    return hits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--leak-check", metavar="RUN_DIR")
    parser.add_argument("--separation-check", metavar="RUN_DIR")
    parser.add_argument("--runs", nargs="*", help="Run directories to analyze (default: all of runs/).")
    args = parser.parse_args()

    if args.leak_check:
        hits = leak_check(Path(args.leak_check))
        if hits == 0:
            print("Leak check passed: 0 hits.")
            sys.exit(0)
        print(f"Leak check FAILED: {hits} hits.")
        sys.exit(1)

    if args.separation_check:
        hits = separation_check(Path(args.separation_check))
        if hits == 0:
            print("Separation check passed: 0 hits.")
            sys.exit(0)
        print(f"Separation check FAILED: {hits} hits.")
        sys.exit(1)

    if args.runs:
        run_dirs = [Path(r) for r in args.runs]
    else:
        run_dirs = sorted(config.RUNS_DIR.iterdir()) if config.RUNS_DIR.exists() else []
    run_dirs = [d for d in run_dirs if d.is_dir() and (d / "log.jsonl").exists()]

    if not run_dirs:
        print("No runs with log.jsonl found.")
        sys.exit(1)

    all_metrics = [compute_metrics_for_run(d) for d in run_dirs]
    write_metrics_csv(all_metrics, config.RESULTS_DIR / "metrics.csv")
    write_h1_events_csv(all_metrics, run_dirs, config.RESULTS_DIR / "h1_events.csv")
    # Figures are built from REAL runs only: dry runs validate plumbing with
    # canned correct-by-construction solutions and would distort every
    # metric they appear in (flat M1 at 1.0, zero tokens).
    real_metrics = [m for m in all_metrics if not Path(m["run_dir"]).name.startswith("dryrun_")]
    if real_metrics:
        plot_cumulative_m1(real_metrics, config.RESULTS_DIR / "cumulative_m1.png")
        plot_m4_counts(real_metrics, config.RESULTS_DIR / "m4_counts.png")
        plot_m4_local_counts(real_metrics, config.RESULTS_DIR / "m4_local_counts.png")
        plot_tokens_per_task(real_metrics, config.RESULTS_DIR / "tokens_per_task.png")
    dump_supersessions(run_dirs, config.RESULTS_DIR)
    for m in all_metrics:
        if m["m4_local_iterations"]:
            fired = ", ".join(f"{e['task_id']} iter{e['iteration']}" for e in m["m4_local_iterations"])
            print(f"M4-local fired in {m['run_dir']} (arm {m['arm']}): {fired}")
    print(f"Analyzed {len(run_dirs)} run(s). Wrote {config.RESULTS_DIR}/metrics.csv and 3 plots.")


if __name__ == "__main__":
    main()
