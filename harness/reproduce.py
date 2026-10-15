"""One-command reproducer: regenerate every number the paper reports, from
the committed run logs, into files under results/.

    python -m harness.reproduce            # all of runs/
    python -m harness.reproduce --runs runs/run_armA_seed1_XXX ...

Writes, under results/:
  metrics.csv            per-(run,task) metrics            (via analyze.py)
  h1_events.csv          per-event H1 violations           (via analyze.py)
  summary_main.csv       per-arm main table (paper Table 1)
  summary_tokens.csv     per-arm token table (paper Table 2)
  leakcheck.txt          hidden-oracle leak scan, per run + total
  separation.txt         separation-of-powers scan, per run + total
  summary.txt            the two tables, rendered, + scan totals

Every number in the paper's abstract and tables is an aggregate of these
files; see REPRODUCE.md for the number->cell map. Aggregates are grouped by
arm over the seeds present, so the output is well-defined for a partial run
too (the per-arm seed count is reported alongside).
"""
import argparse
import csv
from pathlib import Path

from harness import analyze, config
from harness.logging_util import read_log

ARM_ORDER = ["A", "B", "C", "C+", "D"]


def _ordered_arms(present):
    return [a for a in ARM_ORDER if a in present] + sorted(present - set(ARM_ORDER))


def _capture_events(run_dir: Path) -> int:
    return sum(1 for r in read_log(run_dir) if r.get("event") == "capture_event")


def aggregate(run_dirs):
    """Returns {arm: {...}} aggregated over its seeds."""
    per_arm = {}
    for run_dir in run_dirs:
        m = analyze.compute_metrics_for_run(run_dir)
        arm = m["arm"]
        bucket = per_arm.setdefault(arm, {
            "seeds": 0, "m1_at_last": [], "ktok": [],
            "h1_trap": 0, "h1_rewrite": 0, "coerced": 0, "capture": 0,
        })
        bucket["seeds"] += 1

        task_order = m["task_order"]
        last = task_order[-1] if task_order else None
        bucket["m1_at_last"].append(m["m1_cumulative"].get(last, 0.0) if last else 0.0)
        bucket["ktok"].append((m["tokens_in"] + m["tokens_out"]) / 1000.0)

        records = read_log(run_dir)
        events = analyze.compute_h1_events(
            analyze._oracle_events(run_dir, records), task_order,
            records=records, run_dir=run_dir, arm=arm)
        for e in events:
            if e["channel"] == "trap":
                bucket["h1_trap"] += 1
            elif e["channel"] == "rewrite":
                bucket["h1_rewrite"] += 1
            elif e["channel"] == "coerced":
                bucket["coerced"] += 1
        bucket["capture"] += _capture_events(run_dir)

    out = {}
    for arm, b in per_arm.items():
        n = b["seeds"]
        out[arm] = {
            "seeds": n,
            "m1_at_t24": round(sum(b["m1_at_last"]) / n, 3) if n else 0.0,
            "h1_trap": b["h1_trap"],
            "h1_rewrite": b["h1_rewrite"],
            "coerced": b["coerced"],
            "capture": b["capture"],
            "ktok_per_run": round(sum(b["ktok"]) / n, 0) if n else 0.0,
        }
    return out


def write_summaries(agg, results_dir: Path):
    results_dir.mkdir(parents=True, exist_ok=True)
    arms = _ordered_arms(set(agg))

    main_path = results_dir / "summary_main.csv"
    with open(main_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["arm", "n_seeds", "m1_at_t24", "h1_trap", "h1_rewrite",
                    "coerced", "capture", "ktok_per_run"])
        for a in arms:
            r = agg[a]
            w.writerow([a, r["seeds"], r["m1_at_t24"], r["h1_trap"],
                        r["h1_rewrite"], r["coerced"], r["capture"],
                        int(r["ktok_per_run"])])

    base = agg.get("A", {}).get("ktok_per_run") or None
    ledger_b = agg.get("B", {}).get("ktok_per_run") or None
    tokens_path = results_dir / "summary_tokens.csv"
    with open(tokens_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["arm", "ktok_per_run", "x_baseline_A", "x_ledger_B"])
        for a in arms:
            k = agg[a]["ktok_per_run"]
            w.writerow([
                a, int(k),
                round(k / base, 2) if base else "",
                round(k / ledger_b, 2) if ledger_b else "",
            ])
    return main_path, tokens_path, arms


def run_scans(run_dirs, results_dir: Path):
    results_dir.mkdir(parents=True, exist_ok=True)
    leak_total = sep_total = 0
    leak_lines, sep_lines = [], []
    for run_dir in run_dirs:
        lh = analyze.leak_check(run_dir)
        sh = analyze.separation_check(run_dir)
        leak_total += lh
        sep_total += sh
        leak_lines.append(f"{run_dir.name}: {lh} hit(s)")
        sep_lines.append(f"{run_dir.name}: {sh} hit(s)")
    (results_dir / "leakcheck.txt").write_text(
        f"Hidden-oracle leak scan over {len(run_dirs)} run(s)\n"
        f"TOTAL HITS: {leak_total}\n\n" + "\n".join(leak_lines) + "\n",
        encoding="utf-8")
    (results_dir / "separation.txt").write_text(
        f"Separation-of-powers scan over {len(run_dirs)} run(s)\n"
        f"TOTAL HITS: {sep_total}\n\n" + "\n".join(sep_lines) + "\n",
        encoding="utf-8")
    return leak_total, sep_total


def render(agg, arms, leak_total, sep_total, n_runs) -> str:
    lines = [
        f"LedgerBench reproduction summary ({n_runs} run(s))",
        "",
        "Main results (paper Table 1):",
        f"{'Arm':<6}{'seeds':>6}{'M1@T24':>9}{'H1-trap':>9}"
        f"{'H1-rew':>8}{'coerced':>9}{'capture':>9}{'ktok':>7}",
    ]
    for a in arms:
        r = agg[a]
        lines.append(
            f"{a:<6}{r['seeds']:>6}{r['m1_at_t24']:>9}{r['h1_trap']:>9}"
            f"{r['h1_rewrite']:>8}{r['coerced']:>9}{r['capture']:>9}"
            f"{int(r['ktok_per_run']):>7}")
    base = agg.get("A", {}).get("ktok_per_run") or None
    ledger_b = agg.get("B", {}).get("ktok_per_run") or None
    lines += ["", "Token cost (paper Table 2):",
              f"{'Arm':<6}{'ktok':>7}{'xA':>8}{'xB':>8}"]
    for a in arms:
        k = agg[a]["ktok_per_run"]
        xa = f"{k / base:.2f}" if base else "-"
        xb = f"{k / ledger_b:.2f}" if ledger_b else "-"
        lines.append(f"{a:<6}{int(k):>7}{xa:>8}{xb:>8}")
    lines += ["",
              f"Leak scan total hits: {leak_total} (expect 0)",
              f"Separation scan total hits: {sep_total} (expect 0)"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", nargs="*", help="Run dirs (default: all real runs/).")
    args = parser.parse_args()

    if args.runs:
        run_dirs = [Path(r) for r in args.runs]
    else:
        run_dirs = sorted(config.RUNS_DIR.iterdir()) if config.RUNS_DIR.exists() else []
    run_dirs = [d for d in run_dirs
                if d.is_dir() and (d / "log.jsonl").exists()
                and not d.name.startswith("dryrun_")]
    if not run_dirs:
        raise SystemExit("No real runs with log.jsonl found under runs/.")

    # metrics.csv, h1_events.csv, plots, supersessions (reuse analyze.py).
    all_metrics = [analyze.compute_metrics_for_run(d) for d in run_dirs]
    analyze.write_metrics_csv(all_metrics, config.RESULTS_DIR / "metrics.csv")
    analyze.write_h1_events_csv(all_metrics, run_dirs, config.RESULTS_DIR / "h1_events.csv")
    analyze.plot_cumulative_m1(all_metrics, config.RESULTS_DIR / "cumulative_m1.png")
    analyze.plot_tokens_per_task(all_metrics, config.RESULTS_DIR / "tokens_per_task.png")
    analyze.dump_supersessions(run_dirs, config.RESULTS_DIR)

    agg = aggregate(run_dirs)
    _, _, arms = write_summaries(agg, config.RESULTS_DIR)
    leak_total, sep_total = run_scans(run_dirs, config.RESULTS_DIR)

    report = render(agg, arms, leak_total, sep_total, len(run_dirs))
    (config.RESULTS_DIR / "summary.txt").write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {config.RESULTS_DIR}/ : metrics.csv, h1_events.csv, "
          "summary_main.csv, summary_tokens.csv, leakcheck.txt, "
          "separation.txt, summary.txt, plots.")


if __name__ == "__main__":
    main()
