"""Regenerates every empirical number reported in the paper from committed data.

    python -m harness.paper_numbers                 # read results/ + runs/, write outputs
    python -m harness.paper_numbers --isolation     # also re-run leak + separation scans

Inputs (all committed):
  results/metrics.csv, results/h1_events.csv   -- written by `python -m harness.analyze`
  runs/<run_id>/log.jsonl, supersessions.jsonl, ledger.json
  results/isolation_checks.csv                  -- written by --isolation
  logs/campaign*.log                            -- launcher log (infrastructure reruns)
  tasks/taskcli/*.yaml, tasks/taskcli/assertions/ -- the frozen sequence

Outputs:
  results/paper_numbers.json   every number, keyed
  results/claims.md            claim -> value -> source table
  paper/numbers.tex            one LaTeX macro per number; the paper cites only these

Definitions follow the frozen pre-registration (TRAPS.md, commit 257dc61):
H1 counts are over PRIMARY requirements only; `coerced` events are excluded
from H1-rewrite; `conflict` (T24) events are reported separately.
"""
import argparse
import contextlib
import csv
import io
import json
import re
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from harness import analyze, config

ARMS = ["A", "B", "C", "C+", "D"]
LEDGERED = ["B", "C", "C+", "D"]
GOVERNED = ["C", "C+", "D"]
PRIMARIES = ["R9-silence", "R2-order", "R11-exitcodes", "R10-atomic", "R12-pipesafety"]
SECONDARIES = ["R13-archived-export", "R2-ids"]
PLANT = "A11f"
LATE_TASKS = [f"T{i}" for i in range(19, 25)]

RESULTS = config.RESULTS_DIR
RUNS = config.RUNS_DIR
LOGS = config.ROOT_DIR / "logs"
PAPER = config.ROOT_DIR / "paper"


def _arm_of_dirname(name: str) -> str:
    a = name.split("run_arm", 1)[1].split("_", 1)[0]
    return "C+" if a == "Cplus" else a


def load_runs():
    """{run_name: {"arm", "seed", "records", "dir"}} for every completed run in runs/."""
    runs = {}
    for d in sorted(RUNS.iterdir()):
        if not (d / "log.jsonl").exists():
            continue
        records = analyze.read_log(d)
        start = next(r for r in records if r["event"] == "run_start")
        if not any(r["event"] == "run_end" for r in records):
            raise SystemExit(f"incomplete run in runs/: {d.name}")
        runs[d.name] = {"arm": start["arm"], "seed": start["seed"], "records": records, "dir": d}
    return runs


def load_metrics():
    rows = list(csv.DictReader(open(RESULTS / "metrics.csv", encoding="utf-8")))
    for r in rows:
        r["run"] = Path(r["run_dir"]).name
    return rows


def mean_sd(values):
    values = list(values)
    return {
        "n": len(values),
        "mean": st.mean(values),
        "sd": st.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def compute(isolation_rows=None):
    runs = load_runs()
    rows = load_metrics()
    h1 = list(csv.DictReader(open(RESULTS / "h1_events.csv", encoding="utf-8")))
    for e in h1:
        e["run"] = Path(e["run_dir"]).name

    metric_runs = {r["run"] for r in rows}
    if metric_runs != set(runs):
        raise SystemExit("results/metrics.csv does not cover exactly the runs in runs/ -- "
                         "re-run `python -m harness.analyze` first")

    by_run = defaultdict(list)
    for r in rows:
        by_run[r["run"]].append(r)
    runs_by_arm = defaultdict(list)
    for name, info in runs.items():
        runs_by_arm[info["arm"]].append(name)

    N = {}

    # ---- design -----------------------------------------------------------
    starts = [next(r for r in info["records"] if r["event"] == "run_start") for info in runs.values()]
    task_defs = {p.stem: yaml.safe_load(p.read_text(encoding="utf-8"))
                 for p in sorted(config.TASK_DEFS_DIR.glob("T*.yaml"))}
    asserts_per_task = {
        tid: sum(len(re.findall(r"^def test_", (config.TASK_DEFS_DIR / a).read_text(encoding="utf-8"), re.M))
                 for a in td.get("assertions", []))
        for tid, td in task_defs.items()
    }
    oracle_tests_per_task = {
        f.stem.split("_")[0]: len(re.findall(r"^def test_", f.read_text(encoding="utf-8"), re.M))
        for f in sorted(config.ORACLE_DIR.glob("T*_oracle.py"))
    }
    layout_prompts = [
        "## Project layout" in json.loads(r["prompt_full"]).get("system", "")
        for info in runs.values() for r in info["records"] if r["event"] == "api_call"
    ]
    # Declared traps per TRAPS.md ("Declared traps are never adjacent
    # (T15/T17/T19/T21/T23; T18 is undeclared bait...)"). The frozen scorer
    # also files R10's T18 events under channel "trap"; that is reported as-is.
    traps = sorted({s["trap"] for s in analyze.H1_DETECTORS.values() if s["trap"]} - {"T18"},
                   key=lambda t: int(t[1:]))
    N["design"] = {
        "n_tasks": len(task_defs),
        "n_arms": len(runs_by_arm),
        "seeds_per_arm": sorted({len(v) for v in runs_by_arm.values()}),
        "n_runs": len(runs),
        "models": sorted({s["model"] for s in starts}),
        "backends": sorted({s["backend"] for s in starts}),
        "temperatures": sorted({s["temperature"] for s in starts}),
        "max_tokens": sorted({s["max_tokens"] for s in starts}),
        "repair_budget_k": config.REPAIR_BUDGET,
        "max_iterations_observed": max(r["iterations_used"] for info in runs.values()
                                       for r in info["records"] if r["event"] == "task_result"),
        "session_length": 3,
        "trap_tasks": traps,
        "n_trap_tasks": len(traps),
        "primaries": PRIMARIES,
        "secondaries": SECONDARIES,
        "reference_assertion_tests_per_task_min": min(asserts_per_task.values()),
        "reference_assertion_tests_per_task_max": max(asserts_per_task.values()),
        "oracle_tests_per_task_min": min(oracle_tests_per_task.values()),
        "oracle_tests_per_task_max": max(oracle_tests_per_task.values()),
        "oracle_tests_total": sum(oracle_tests_per_task.values()),
        "peak_call_tokens": max(r["usage"]["input_tokens"] + r["usage"]["output_tokens"]
                                for info in runs.values() for r in info["records"] if "usage" in r and isinstance(r["usage"], dict)),
        "generator_calls_total": len(layout_prompts),
        "generator_calls_with_layout_block": sum(layout_prompts),
    }

    # ---- per-arm outcome metrics -----------------------------------------
    def per_run(arm, fn):
        return [fn(name) for name in sorted(runs_by_arm[arm], key=lambda n: runs[n]["seed"])]

    def task_row(name, tid):
        return next(r for r in by_run[name] if r["task_id"] == tid)

    def tokens(name):
        r = by_run[name][0]
        return int(r["tokens_in_total"]) + int(r["tokens_out_total"])

    arms = {}
    for arm in ARMS:
        A = {}
        A["n_runs"] = len(runs_by_arm[arm])
        A["m1_at_T24"] = mean_sd(per_run(arm, lambda n: float(task_row(n, "T24")["m1_cumulative"])))
        A["m1_at_T24_by_seed"] = per_run(arm, lambda n: float(task_row(n, "T24")["m1_cumulative"]))
        A["m1_task_pass_rate"] = mean_sd(per_run(arm, lambda n: st.mean(r["m1_pass"] == "True" for r in by_run[n])))
        A["arm_verdict_pass_rate"] = mean_sd(per_run(arm, lambda n: st.mean(r["arm_verdict"] == "PASS" for r in by_run[n])))
        A["m2_regressions_per_run"] = mean_sd(per_run(arm, lambda n: sum(int(r["m2_regression_count"]) for r in by_run[n])))
        A["m2_late_T19_T24_total"] = sum(int(r["m2_regression_count"]) for n in runs_by_arm[arm]
                                         for r in by_run[n] if r["task_id"] in LATE_TASKS)
        A["m4_strict_total"] = sum(int(r["m4_strict_count"]) for n in runs_by_arm[arm] for r in by_run[n])
        A["m4_local_total"] = sum(int(r["m4_local_count"]) for n in runs_by_arm[arm] for r in by_run[n])
        A["m4_local_T14_onward_total"] = sum(int(r["m4_local_count"]) for n in runs_by_arm[arm]
                                             for r in by_run[n] if int(r["task_id"][1:]) >= 14)
        A["mean_repair_iterations"] = mean_sd(per_run(arm, lambda n: float(by_run[n][0]["mean_repair_iterations"])))
        A["tokens_per_run"] = mean_sd(per_run(arm, tokens))
        A["ktok_per_run"] = A["tokens_per_run"]["mean"] / 1000
        A["wall_minutes_per_run"] = mean_sd(per_run(arm, lambda n: (runs[n]["records"][-1]["ts"] - runs[n]["records"][0]["ts"]) / 60))

        vest = [r["vestigial_code"] for n in runs_by_arm[arm] for r in by_run[n] if r["vestigial_code"] in ("True", "False")]
        A["vestigial_post_T20_commits"] = len(vest)
        A["vestigial_post_T20_retaining"] = sum(v == "True" for v in vest)
        A["vestigial_post_T20_pct"] = 100 * A["vestigial_post_T20_retaining"] / len(vest) if vest else None

        # H1 (primaries confirmatory; secondaries exploratory)
        ev = [e for e in h1 if e["arm"] == arm]
        def cnt(reqs, channel, grade=None):
            return sum(1 for e in ev if e["requirement"] in reqs and e["channel"] == channel
                       and (grade is None or e["bite_grade"] == grade))
        A["h1_trap_primary"] = cnt(PRIMARIES, "trap")
        A["h1_rewrite_primary"] = cnt(PRIMARIES, "rewrite")
        A["h1_coerced_primary"] = cnt(PRIMARIES, "coerced")
        A["h1_conflict_primary"] = cnt(PRIMARIES, "conflict")
        A["h1_trap_secondary"] = cnt(SECONDARIES, "trap")
        A["h1_rewrite_secondary"] = cnt(SECONDARIES, "rewrite")
        # Sensitivity (not pre-registered): coerced events put back at the
        # channel position they occurred in (trap task vs elsewhere).
        trap_of = {req: spec["trap"] for req, spec in analyze.H1_DETECTORS.items()}
        A["h1_coerced_at_trap_task"] = sum(1 for e in ev if e["requirement"] in PRIMARIES and e["channel"] == "coerced" and e["task"] == trap_of[e["requirement"]])
        A["h1_coerced_elsewhere"] = A["h1_coerced_primary"] - A["h1_coerced_at_trap_task"]
        A["h1_trap_incl_coerced"] = A["h1_trap_primary"] + A["h1_coerced_at_trap_task"]
        A["h1_rewrite_incl_coerced"] = A["h1_rewrite_primary"] + A["h1_coerced_elsewhere"]
        A["h1_contract_grade_primary"] = sum(cnt(PRIMARIES, c, "contract") for c in ("trap", "rewrite"))
        A["h1_trap_by_primary"] = {req: sum(1 for e in ev if e["requirement"] == req and e["channel"] == "trap")
                                   for req in PRIMARIES}
        A["h1_by_primary"] = {req: sum(1 for e in ev if e["requirement"] == req and e["channel"] in ("trap", "rewrite"))
                              for req in PRIMARIES}

        # governance activity from the logs
        rec = [r for n in runs_by_arm[arm] for r in runs[n]["records"]]
        judge = [r for r in rec if r["event"] == "judge_call"]
        A["m6_supersede"] = sum(r["verdict"] == "SUPERSEDE" for r in judge)
        A["m6_retain"] = sum(r["verdict"] != "SUPERSEDE" for r in judge)
        A["m6_conflict_escalations"] = sum(r["event"] == "conflict_unresolved" for r in rec)
        A["judge_calls_by_kind"] = dict(Counter(f'{r.get("kind")}:{r["verdict"]}' for r in judge))
        A["telemetry_dockets"] = sum(r["event"] == "telemetry_docket" for r in rec)
        A["retire_requests"] = sum(r["event"] == "retire_request" for r in rec)
        A["retire_requests_known_assertion"] = sum(r["event"] == "retire_request" and r.get("known_assertion") for r in rec)
        A["capture_events"] = sum(r["event"] == "capture_event" for r in rec)

        # supersession routes, plant A11f, regime changes
        sups = {n: [json.loads(l) for l in (runs[n]["dir"] / "supersessions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
                if (runs[n]["dir"] / "supersessions.jsonl").exists() else [] for n in runs_by_arm[arm]}
        route = lambda s: ("evidence" if s["evidence_id"].startswith("E") else s["evidence_id"])
        A["supersessions_by_route"] = dict(Counter(route(s) for v in sups.values() for s in v))

        def admitted(n, aid):
            p = runs[n]["dir"] / "ledger.json"
            return p.exists() and any(e["meta"]["id"] == aid for e in json.loads(p.read_text(encoding="utf-8")))
        a11f = Counter()
        for n, v in sups.items():
            hit = [s for s in v if s["assertion_id"] == PLANT]
            if not admitted(n, PLANT):
                a11f["not_admitted"] += 1
            elif hit:
                a11f[f"superseded_{route(hit[0])}"] += 1
            else:
                a11f["retained"] += 1
        A["a11f_outcomes"] = dict(a11f)

        def sup_by(n, aid, ev_id, task):
            return any(s["assertion_id"] == aid and s["evidence_id"] == ev_id and s["task"] == task for s in sups[n])
        A["e2_supersedes_A6_and_A10_at_T14_runs"] = sum(sup_by(n, "A6", "E2", "T14") and sup_by(n, "A10", "E2", "T14") for n in runs_by_arm[arm])
        A["e2_supersedes_A6_at_T14_runs"] = sum(sup_by(n, "A6", "E2", "T14") for n in runs_by_arm[arm])
        A["a10_superseded_before_T14_runs"] = sum(any(s["assertion_id"] == "A10" and int(s["task"][1:]) < 14 for s in sups[n]) for n in runs_by_arm[arm])
        A["a10_superseded_by_T14_any_route_runs"] = sum(any(s["assertion_id"] == "A10" and int(s["task"][1:]) <= 14 for s in sups[n]) for n in runs_by_arm[arm])
        A["a11f_docketed_runs"] = sum(any(r["event"] == "telemetry_docket" and r["assertion_id"] == PLANT for r in runs[n]["records"]) for n in runs_by_arm[arm])
        A["e3_supersedes_A5_at_T20_runs"] = sum(sup_by(n, "A5", "E3", "T20") for n in runs_by_arm[arm])
        A["e1_supersedes_A1_A3_A4_at_T6_runs"] = sum(all(sup_by(n, a, "E1", "T6") for a in ("A1", "A3", "A4")) for n in runs_by_arm[arm])

        # T24 conflict
        t24 = [r for n in runs_by_arm[arm] for r in runs[n]["records"] if r["event"] == "task_result" and r["task_id"] == "T24"]
        A["t24_failed_full_budget_runs"] = sum(r["verdict"] == "FAILED" and r["iterations_used"] == config.REPAIR_BUDGET for r in t24)
        A["t24_conflict_escalation_runs"] = sum(any(r["event"] == "conflict_unresolved" and r["task_id"] == "T24" for r in runs[n]["records"]) for n in runs_by_arm[arm])
        arms[arm] = A
    N["arms"] = arms

    # ---- cross-arm ratios and pre-registered verdicts --------------------
    a = arms["A"]
    third_trap, third_rewrite = a["h1_trap_primary"] / 3, a["h1_rewrite_primary"] / 3
    N["ratios"] = {
        "tokens_B_over_A": arms["B"]["ktok_per_run"] / a["ktok_per_run"],
        "tokens_A_over_B": a["ktok_per_run"] / arms["B"]["ktok_per_run"],
        **{f"tokens_{x}_over_B_pct": 100 * arms[x]["ktok_per_run"] / arms["B"]["ktok_per_run"] for x in GOVERNED},
        **{f"trap_reduction_{x}_vs_A_pct": (100 * (1 - arms[x]["h1_trap_primary"] / a["h1_trap_primary"])
                                            if a["h1_trap_primary"] else None) for x in LEDGERED},
    }
    verdicts = {}
    for x in LEDGERED:
        verdicts[f"h1_trap_{x}"] = {"count": arms[x]["h1_trap_primary"], "threshold": third_trap,
                                    "confirmed": arms[x]["h1_trap_primary"] <= third_trap}
        verdicts[f"h1_rewrite_{x}"] = {"count": arms[x]["h1_rewrite_primary"], "threshold": third_rewrite,
                                       "confirmed": arms[x]["h1_rewrite_primary"] <= third_rewrite}
    sens = {}
    for x in LEDGERED:
        sens[f"h1_trap_{x}"] = {"count": arms[x]["h1_trap_incl_coerced"], "threshold": third_trap,
                                "confirmed": arms[x]["h1_trap_incl_coerced"] <= third_trap}
        sens[f"h1_rewrite_{x}"] = {"count": arms[x]["h1_rewrite_incl_coerced"], "threshold": third_rewrite,
                                   "confirmed": arms[x]["h1_rewrite_incl_coerced"] <= third_rewrite}
    N["sensitivity_verdicts_incl_coerced"] = sens
    verdicts["d_capture_positive"] = arms["D"]["capture_events"] > 0
    verdicts["c_capture_zero"] = arms["C"]["capture_events"] == 0
    verdicts["d_late_regression_ge_c"] = arms["D"]["m2_late_T19_T24_total"] >= arms["C"]["m2_late_T19_T24_total"]
    verdicts["c_retains_a11f_every_run"] = arms["C"]["a11f_outcomes"].get("retained", 0) == arms["C"]["n_runs"]
    verdicts["cplus_dockets_a11f_some_run"] = arms["C+"]["a11f_docketed_runs"] > 0
    verdicts["t14_B_blocks_valid_work"] = arms["B"]["m4_local_T14_onward_total"] > 0
    verdicts["t14_Cfamily_supersede_A6_every_run"] = all(arms[x]["e2_supersedes_A6_at_T14_runs"] == arms[x]["n_runs"] for x in GOVERNED)
    verdicts["t14_Cfamily_A10_gone_by_T14_every_run"] = all(arms[x]["a10_superseded_by_T14_any_route_runs"] == arms[x]["n_runs"] for x in GOVERNED)
    verdicts["t24_B_thrashes_every_run"] = arms["B"]["t24_failed_full_budget_runs"] == arms["B"]["n_runs"]
    verdicts["t24_Cfamily_escalates_every_run"] = all(arms[x]["t24_conflict_escalation_runs"] == arms[x]["n_runs"] for x in GOVERNED)
    verdicts["r10_violations_all_contract_grade"] = all(
        sum(1 for e in h1 if e["arm"] == x and e["requirement"] == "R10-atomic" and e["channel"] in ("trap", "rewrite") and e["bite_grade"] != "contract") == 0
        for x in ARMS)
    verdicts["coercion_only_in_B"] = all(arms[x]["h1_coerced_primary"] == 0 for x in ARMS if x != "B")
    verdicts["vestigial_B_gt_Cfamily_gt_A"] = (
        arms["B"]["vestigial_post_T20_pct"] > max(arms[x]["vestigial_post_T20_pct"] for x in GOVERNED)
        and min(arms[x]["vestigial_post_T20_pct"] for x in GOVERNED) > a["vestigial_post_T20_pct"])
    N["preregistered_verdicts"] = verdicts

    # ---- statistics (exploratory: the pre-registration put inference out of scope) --
    def h1_per_run(name, channels):
        return sum(1 for e in h1 if e["run"] == name and e["requirement"] in PRIMARIES and e["channel"] in channels)
    endpoints = {
        "m1_t24": lambda n: float(task_row(n, "T24")["m1_cumulative"]),
        "m1_pass_rate": lambda n: st.mean(r["m1_pass"] == "True" for r in by_run[n]),
        "regressions": lambda n: sum(int(r["m2_regression_count"]) for r in by_run[n]),
        "h1_trap_rewrite": lambda n: h1_per_run(n, ("trap", "rewrite")),
        "h1_incl_coerced": lambda n: h1_per_run(n, ("trap", "rewrite", "coerced")),
        "ktok": lambda n: tokens(n) / 1000,
    }
    N["stats"] = inference({ep: {arm: per_run(arm, fn) for arm in ARMS} for ep, fn in endpoints.items()})

    # ---- isolation -------------------------------------------------------
    if isolation_rows is None and (RESULTS / "isolation_checks.csv").exists():
        isolation_rows = list(csv.DictReader(open(RESULTS / "isolation_checks.csv", encoding="utf-8")))
    if isolation_rows:
        gov = [r for r in isolation_rows if r["arm"] in GOVERNED]
        N["isolation"] = {
            "leak_runs_scanned": len(isolation_rows),
            "leak_hits": sum(int(r["leak_hits"]) for r in isolation_rows),
            "separation_runs_scanned_all": len(isolation_rows),
            "separation_hits_all": sum(int(r["separation_hits"]) for r in isolation_rows),
            "separation_governed_runs_scanned": len(gov),
            "separation_governed_hits": sum(int(r["separation_hits"]) for r in gov),
        }

    # ---- infrastructure (launcher log) ----------------------------------
    starts_log = Counter()
    for p in sorted(LOGS.glob("campaign*.log")):
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.search(r"START arm=(\S+) seed=(\d+)", line)
            if m:
                starts_log[(m.group(1), int(m.group(2)))] += 1
    N["infrastructure"] = {
        "pairs_started": len(starts_log),
        "infrastructure_reruns": sum(c - 1 for c in starts_log.values()),
        "rerun_pairs": sorted(f"{a}/seed{s}" for (a, s), c in starts_log.items() if c > 1),
    }
    excluded = {}
    for d in sorted(config.ROOT_DIR.glob("runs_*")):
        excluded[d.name] = len([x for x in d.iterdir() if (x / "log.jsonl").exists()])
    N["excluded_attempts"] = excluded
    return N


def _cliffs_delta(x, y):
    gt = sum(1 for a in x for b in y if a > b)
    lt = sum(1 for a in x for b in y if a < b)
    return (gt - lt) / (len(x) * len(y))


def _bootstrap_ci(x, y=None, reps=10000, seed=20260924):
    """Percentile 95% CI of mean(x) or of mean(x) - mean(y); fixed seed so reruns match."""
    import random
    rng = random.Random(seed)
    stats_ = []
    for _ in range(reps):
        bx = [rng.choice(x) for _ in x]
        stats_.append(st.mean(bx) - (st.mean([rng.choice(y) for _ in y]) if y is not None else 0))
    stats_.sort()
    return [stats_[int(0.025 * reps)], stats_[int(0.975 * reps) - 1]]


def _holm(pvals: dict) -> dict:
    order = sorted(pvals, key=pvals.get)
    m, running, out = len(order), 0.0, {}
    for i, k in enumerate(order):
        running = max(running, min(1.0, (m - i) * pvals[k]))
        out[k] = running
    return out


def inference(data):
    """Per endpoint: per-arm mean + bootstrap CI; Kruskal-Wallis across arms;
    two families of two-sided Mann-Whitney U tests with Holm correction --
    each ledgered arm vs A (4 tests), and all pairs among ledgered arms (6)."""
    from itertools import combinations
    from scipy.stats import kruskal, mannwhitneyu
    out = {}
    for ep, by_arm in data.items():
        E = {"arms": {a: {"mean": st.mean(v), "ci95": _bootstrap_ci(v)} for a, v in by_arm.items()}}
        E["kruskal_H"], E["kruskal_p"] = map(float, kruskal(*by_arm.values()))
        for fam, pairs in (("vs_A", [(x, "A") for x in LEDGERED]),
                           ("among_ledgered", list(combinations(LEDGERED, 2)))):
            raw, rows = {}, {}
            for x, y in pairs:
                key = f"{x}_vs_{y}"
                u, p = mannwhitneyu(by_arm[x], by_arm[y], alternative="two-sided")
                raw[key] = float(p)
                rows[key] = {"U": float(u), "p": float(p), "cliffs_delta": _cliffs_delta(by_arm[x], by_arm[y]),
                             "mean_diff": st.mean(by_arm[x]) - st.mean(by_arm[y]),
                             "mean_diff_ci95": _bootstrap_ci(by_arm[x], by_arm[y])}
            for key, p in _holm(raw).items():
                rows[key]["p_holm"] = p
                rows[key]["significant_0_05"] = p < 0.05
            E[fam] = rows
        out[ep] = E
    return out


def run_isolation(runs):
    rows = []
    for name, info in sorted(runs.items()):
        with contextlib.redirect_stdout(io.StringIO()):
            leak = analyze.leak_check(info["dir"])
            sep = analyze.separation_check(info["dir"])
        rows.append({"run": name, "arm": info["arm"], "seed": info["seed"],
                     "leak_hits": leak, "separation_hits": sep})
        print(f"isolation {name}: leak={leak} separation={sep}")
    with open(RESULTS / "isolation_checks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return [{k: str(v) for k, v in r.items()} for r in rows]


# ---- outputs -------------------------------------------------------------

def _macro_name(key: str) -> str:
    """LaTeX macro names may only contain letters: 'C+'->Cplus, digits spelled."""
    digits = "Zero One Two Three Four Five Six Seven Eight Nine".split()
    key = key.replace("C+", "Cplus").replace("+", "plus")
    out, up = "", True
    for ch in key:
        if ch.isdigit():
            out += digits[int(ch)]; up = True
        elif ch.isalpha():
            out += ch.upper() if up else ch; up = False
        else:
            up = True
    return "N" + out


def _fmt(v, nd=3):
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.{nd}f}".rstrip("0").rstrip(".") if v != int(v) else str(int(v))
    return str(v)


def claims(N):
    """(key, description, value, source) rows; the key becomes the LaTeX macro."""
    C = []
    d = N["design"]
    src_runs = "runs/*/log.jsonl (run_start)"
    C += [
        ("nTasks", "Tasks in the fixed sequence", d["n_tasks"], "tasks/taskcli/T*.yaml"),
        ("nArms", "Arms compared", d["n_arms"], src_runs),
        ("seedsPerArm", "Seeds (independent repeats) per arm", d["seeds_per_arm"][0], src_runs),
        ("nRuns", "Completed runs analyzed", d["n_runs"], src_runs),
        ("model", "Generator/judge model tag", d["models"][0], src_runs),
        ("temperature", "Sampling temperature", d["temperatures"][0], src_runs),
        ("maxTokens", "Max output tokens per call", d["max_tokens"][0], src_runs),
        ("repairBudget", "Repair budget k", d["repair_budget_k"], "harness/config.py; max iterations_used in logs"),
        ("nTrapTasks", "Declared (non-adjacent) trap tasks", d["n_trap_tasks"], "harness/analyze.py H1_DETECTORS"),
        ("assertMin", "Reference assertion tests per task (min)", d["reference_assertion_tests_per_task_min"], "tasks/taskcli/assertions"),
        ("assertMax", "Reference assertion tests per task (max)", d["reference_assertion_tests_per_task_max"], "tasks/taskcli/assertions"),
        ("oracleMin", "Hidden oracle tests per task (min)", d["oracle_tests_per_task_min"], "oracles/taskcli"),
        ("oracleMax", "Hidden oracle tests per task (max)", d["oracle_tests_per_task_max"], "oracles/taskcli"),
        ("oracleTotal", "Hidden oracle tests in total", d["oracle_tests_total"], "oracles/taskcli"),
        ("peakCallTokens", "Largest prompt+output of any model call (tokens; context window 131072)", d["peak_call_tokens"], "runs/*/log.jsonl (usage)"),
        ("generatorCalls", "Generator calls (all runs)", d["generator_calls_total"], "runs/*/log.jsonl (api_call)"),
        ("layoutCalls", "Generator calls whose system prompt carried the layout block", d["generator_calls_with_layout_block"], "runs/*/log.jsonl (api_call prompt_full)"),
    ]
    for arm, A in N["arms"].items():
        k = arm
        m = A["m1_at_T24"]
        C += [
            (f"mOneTwentyFour{k}", f"M1@T24 mean, Arm {arm}", round(m["mean"], 3), "results/metrics.csv (m1_cumulative @T24)"),
            (f"mOneTwentyFourSd{k}", f"M1@T24 SD, Arm {arm}", round(m["sd"], 3), "results/metrics.csv"),
            (f"mOnePass{k}", f"Per-task hidden-oracle pass rate, Arm {arm}", round(A["m1_task_pass_rate"]["mean"], 3), "results/metrics.csv (m1_pass)"),
            (f"verdictPass{k}", f"Arm's own verdict pass rate, Arm {arm}", round(A["arm_verdict_pass_rate"]["mean"], 3), "results/metrics.csv (arm_verdict)"),
            (f"regressions{k}", f"M2 regressions per run (mean), Arm {arm}", round(A["m2_regressions_per_run"]["mean"], 1), "results/metrics.csv (m2_regression_count)"),
            (f"trap{k}", f"H1-trap violations (primaries), Arm {arm}", A["h1_trap_primary"], "results/h1_events.csv"),
            (f"rewrite{k}", f"H1-rewrite violations (primaries, uncoerced), Arm {arm}", A["h1_rewrite_primary"], "results/h1_events.csv"),
            (f"coerced{k}", f"Coerced regressions (excluded), Arm {arm}", A["h1_coerced_primary"], "results/h1_events.csv"),
            (f"conflictEv{k}", f"H1 events at T24 conflict (primaries), Arm {arm}", A["h1_conflict_primary"], "results/h1_events.csv"),
            (f"ktok{k}", f"Tokens per run (thousands, in+out), Arm {arm}", round(A["ktok_per_run"]), "results/metrics.csv (tokens_*_total)"),
            (f"mFourLocal{k}", f"M4-local blocked-valid-solution iterations, Arm {arm}", A["m4_local_total"], "results/metrics.csv (m4_local_count)"),
            (f"mFourStrict{k}", f"M4-strict blocked-valid-solution iterations, Arm {arm}", A["m4_strict_total"], "results/metrics.csv (m4_strict_count)"),
            (f"lateRegress{k}", f"M2 regressions at T19-T24 (total), Arm {arm}", A["m2_late_T19_T24_total"], "results/metrics.csv"),
            (f"vestigialPct{k}", f"Post-T20 task-final commits retaining TASKCLI_TODAY (%), Arm {arm}", round(A["vestigial_post_T20_pct"], 1), "results/metrics.csv (vestigial_code)"),
            (f"wallMin{k}", f"Wall-clock minutes per run (mean), Arm {arm}", round(A["wall_minutes_per_run"]["mean"]), "runs/*/log.jsonl (ts)"),
        ]
        for req, n in A["h1_by_primary"].items():
            C.append((f"hOne_{req}_{k}", f"H1 trap+rewrite violations on {req}, Arm {arm}", n, "results/h1_events.csv"))
        C.append((f"trapInclCoerced{k}", f"Sensitivity: trap-position violations incl. coerced, Arm {arm}", A["h1_trap_incl_coerced"], "results/h1_events.csv"))
        C.append((f"rewriteInclCoerced{k}", f"Sensitivity: rewrite-position violations incl. coerced, Arm {arm}", A["h1_rewrite_incl_coerced"], "results/h1_events.csv"))
        for req, n in A["h1_trap_by_primary"].items():
            C.append((f"trapOn_{req}_{k}", f"H1-trap violations on {req}, Arm {arm}", n, "results/h1_events.csv"))
        C.append((f"contractGrade{k}", f"Contract-grade H1 violations (primaries), Arm {arm}", A["h1_contract_grade_primary"], "results/h1_events.csv (bite_grade)"))
        C.append((f"trapSecondary{k}", f"H1-trap violations (secondaries, exploratory), Arm {arm}", A["h1_trap_secondary"], "results/h1_events.csv"))
        C.append((f"rewriteSecondary{k}", f"H1-rewrite violations (secondaries, exploratory), Arm {arm}", A["h1_rewrite_secondary"], "results/h1_events.csv"))
        if arm in GOVERNED:
            C += [
                (f"aTenByFourteen{k}", f"Runs where A10 was superseded by T14 (any route), Arm {arm}", A["a10_superseded_by_T14_any_route_runs"], "runs/*/supersessions.jsonl"),
                (f"plantDocketed{k}", f"Runs where A11f was docketed, Arm {arm}", A["a11f_docketed_runs"], "runs/*/log.jsonl (telemetry_docket)"),
                (f"supersede{k}", f"Judge SUPERSEDE verdicts, Arm {arm}", A["m6_supersede"], "runs/*/log.jsonl (judge_call)"),
                (f"retain{k}", f"Judge RETAIN verdicts, Arm {arm}", A["m6_retain"], "runs/*/log.jsonl (judge_call)"),
                (f"escalations{k}", f"Conflict escalations (conflict_unresolved), Arm {arm}", A["m6_conflict_escalations"], "runs/*/log.jsonl"),
                (f"capture{k}", f"Capture events, Arm {arm}", A["capture_events"], "runs/*/log.jsonl (capture_event)"),
                (f"plantRetained{k}", f"Runs retaining plant A11f to T24, Arm {arm}", A["a11f_outcomes"].get("retained", 0), "runs/*/ledger.json + supersessions.jsonl"),
                (f"eTwoBoth{k}", f"Runs where E2 superseded A6 and A10 at T14, Arm {arm}", A["e2_supersedes_A6_and_A10_at_T14_runs"], "runs/*/supersessions.jsonl"),
                (f"eTwoASix{k}", f"Runs where E2 superseded A6 at T14, Arm {arm}", A["e2_supersedes_A6_at_T14_runs"], "runs/*/supersessions.jsonl"),
                (f"aTenEarly{k}", f"Runs where A10 was superseded before T14, Arm {arm}", A["a10_superseded_before_T14_runs"], "runs/*/supersessions.jsonl"),
                (f"eOne{k}", f"Runs where E1 superseded A1, A3 and A4 at T6, Arm {arm}", A["e1_supersedes_A1_A3_A4_at_T6_runs"], "runs/*/supersessions.jsonl"),
                (f"eThree{k}", f"Runs where E3 superseded A5 at T20, Arm {arm}", A["e3_supersedes_A5_at_T20_runs"], "runs/*/supersessions.jsonl"),
                (f"tTwentyFourEsc{k}", f"Runs escalating a conflict at T24, Arm {arm}", A["t24_conflict_escalation_runs"], "runs/*/log.jsonl"),
            ]
        for route, n in A["a11f_outcomes"].items():
            if route.startswith("superseded_"):
                C.append((f"plant{route.split('_', 1)[1].title().replace('-', '')}{k}",
                          f"Runs superseding A11f via {route.split('_', 1)[1]}, Arm {arm}", n, "runs/*/supersessions.jsonl"))
    C += [
        ("docketCplus", "Telemetry dockets opened, Arm C+", N["arms"]["C+"]["telemetry_dockets"], "runs/*/log.jsonl (telemetry_docket)"),
        ("retireReqD", "Generator retirement requests, Arm D", N["arms"]["D"]["retire_requests"], "runs/*/log.jsonl (retire_request)"),
        ("retireKnownD", "Retirement requests naming an active assertion, Arm D", N["arms"]["D"]["retire_requests_known_assertion"], "runs/*/log.jsonl"),
        ("tTwentyFourThrashB", "Arm B runs exhausting the repair budget at T24", N["arms"]["B"]["t24_failed_full_budget_runs"], "runs/*/log.jsonl (task_result)"),
        ("mFourLocalBFromTFourteen", "Arm B M4-local iterations at T14 onward", N["arms"]["B"]["m4_local_T14_onward_total"], "results/metrics.csv"),
    ]
    r = N["ratios"]
    C += [
        ("tokRatioBA", "Token cost ratio B / A", round(r["tokens_B_over_A"], 2), "derived: ktokB / ktokA"),
        ("tokRatioAB", "Token cost ratio A / B", round(r["tokens_A_over_B"], 2), "derived"),
    ]
    for x in GOVERNED:
        C.append((f"tokPctOfB{x}", f"Token cost of Arm {x} as % of B", round(r[f"tokens_{x}_over_B_pct"]), "derived"))
    for x in LEDGERED:
        v = r[f"trap_reduction_{x}_vs_A_pct"]
        if v is not None:
            C.append((f"trapReduction{x}", f"H1-trap reduction vs A (%), Arm {x}", round(v), "derived"))
    for key, v in N["preregistered_verdicts"].items():
        if isinstance(v, dict):
            C.append((f"verdict_{key}", f"Pre-registered {key}: count {v['count']} vs threshold {v['threshold']:.2f}",
                      "CONFIRMED" if v["confirmed"] else "REFUTED", "derived (TRAPS.md pre-registration)"))
        else:
            C.append((f"verdict_{key}", f"Pre-registered check {key}", "yes" if v else "no", "derived"))
    def fp(p):
        return "<0.001" if p < 0.001 else f"{p:.3f}"
    ep_names = {"m1_t24": "mOneTwentyFour", "m1_pass_rate": "mOnePass", "regressions": "regressions",
                "h1_trap_rewrite": "hOne", "h1_incl_coerced": "hOneInclCoerced", "ktok": "ktok"}
    for ep, E in N["stats"].items():
        tag = ep_names[ep]
        C.append((f"st_{tag}_kwP", f"{ep}: Kruskal-Wallis p across 5 arms", fp(E["kruskal_p"]), "derived (scipy.stats.kruskal)"))
        for arm, v in E["arms"].items():
            lo, hi = v["ci95"]
            C.append((f"st_{tag}_ci_{arm}", f"{ep}: bootstrap 95% CI of mean, Arm {arm}",
                      (f"[{lo:.0f}, {hi:.0f}]" if abs(hi) >= 100 else f"[{lo:.3g}, {hi:.3g}]"),
                      "derived (percentile bootstrap, 10k, fixed seed)"))
        for fam in ("vs_A", "among_ledgered"):
            for key, r in E[fam].items():
                k = key.replace("_vs_", "vs")
                C.append((f"st_{tag}_{k}_pHolm", f"{ep}: {key} Mann-Whitney p (Holm, family {fam})",
                          fp(r["p_holm"]), "derived (scipy.stats.mannwhitneyu + Holm)"))
                C.append((f"st_{tag}_{k}_delta", f"{ep}: {key} Cliff's delta", round(r["cliffs_delta"], 2), "derived"))
    for key, v in N["sensitivity_verdicts_incl_coerced"].items():
        C.append((f"sens_{key}", f"Sensitivity {key} incl. coerced: count {v['count']} vs threshold {v['threshold']:.2f}",
                  "CONFIRMED" if v["confirmed"] else "REFUTED", "derived (not pre-registered)"))
    C.append(("trapThreshold", "Pre-registered H1-trap threshold (A/3)", round(N["preregistered_verdicts"]["h1_trap_B"]["threshold"], 2), "derived"))
    C.append(("rewriteThreshold", "Pre-registered H1-rewrite threshold (A/3)", round(N["preregistered_verdicts"]["h1_rewrite_B"]["threshold"], 2), "derived"))
    if "isolation" in N:
        i = N["isolation"]
        C += [
            ("leakRuns", "Runs leak-scanned", i["leak_runs_scanned"], "results/isolation_checks.csv"),
            ("leakHits", "Leak-check hits", i["leak_hits"], "results/isolation_checks.csv"),
            ("sepGovRuns", "Governed runs separation-scanned", i["separation_governed_runs_scanned"], "results/isolation_checks.csv"),
            ("sepGovHits", "Separation-of-powers hits (governed runs)", i["separation_governed_hits"], "results/isolation_checks.csv"),
        ]
    inf = N["infrastructure"]
    C += [("infraReruns", "Infrastructure reruns (same seed)", inf["infrastructure_reruns"], "logs/campaign*.log")]
    for name, n in N["excluded_attempts"].items():
        C.append((f"excluded{name}", f"Excluded attempt runs in {name}/", n, f"{name}/"))
    return C


def write_outputs(N):
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "paper_numbers.json").write_text(json.dumps(N, indent=2, default=str), encoding="utf-8")
    rows = claims(N)
    md = ["# Claims table", "",
          "Generated by `python -m harness.paper_numbers`; do not edit by hand.",
          "Each number in the paper is a `\\N...` macro from `paper/numbers.tex`, listed here with its source.", "",
          "| Macro | Claim | Value | Source |", "|---|---|---|---|"]
    tex = ["% Generated by `python -m harness.paper_numbers` from committed data. Do not edit.", ""]
    seen = set()
    for key, desc, val, src in rows:
        macro = _macro_name(key)
        if macro in seen:
            raise SystemExit(f"duplicate macro {macro} for {key}")
        seen.add(macro)
        md.append(f"| `\\{macro}` | {desc} | {_fmt(val)} | `{src}` |")
        tex.append(f"\\newcommand{{\\{macro}}}{{{_fmt(val).replace('_', chr(92) + '_')}}}")
    (RESULTS / "claims.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    PAPER.mkdir(exist_ok=True)
    (PAPER / "numbers.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")
    print(f"Wrote results/paper_numbers.json, results/claims.md ({len(rows)} claims), paper/numbers.tex")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--isolation", action="store_true", help="re-run leak and separation scans on every run")
    args = p.parse_args()
    iso = run_isolation(load_runs()) if args.isolation else None
    write_outputs(compute(iso))


if __name__ == "__main__":
    main()
