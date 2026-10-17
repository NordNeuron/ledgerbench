# LedgerBench run data

Everything the paper (`paper/ledgerbench-qwen.tex`) reports is derived from
the files in this directory and `results/`, by the commands at the bottom.

## Main campaign — `data/runs/`

| Archive | Contents |
|---|---|
| `armA.tar.xz` | `runs/run_armA_seed{1..12}_*` |
| `armB.tar.xz` | `runs/run_armB_seed{1..12}_*` |
| `armC.tar.xz` | `runs/run_armC_seed{1..12}_*` |
| `armCplus.tar.xz` | `runs/run_armCplus_seed{1..12}_*` (arm C+) |
| `armD.tar.xz` | `runs/run_armD_seed{1..12}_*` |

Each run directory holds:

- `log.jsonl` — every event in order: `run_start` (model, backend,
  temperature, max tokens), every generator/summary/judge call with the
  **complete prompt and response** and provider token usage, every
  verification (ledger) result, every hidden-oracle result, task verdicts,
  smoke probes, and governance events (`judge_call`, `conflict_unresolved`,
  `telemetry_docket`, `retire_request`, `capture_event`, `audit_pool_results`).
- `workspace/` — the project the agent edited, as a git repository with one
  commit per repair iteration (`T<n> iter<k>`), so every intermediate state can
  be checked out and re-scored.
- `ledger.json`, `supersessions.jsonl` — ledgered arms only: admitted
  assertions and every retirement, with route (`E1`/`E2`/`E3` evidence,
  `conflict`, `telemetry-docket`, `generator-lobby`) and the judge's reason.
  Recorded assertion paths are absolute paths on the original machine; the
  analysis resolves them to `tasks/taskcli/assertions/` by file name.

Configuration (identical for all 60 runs):

| Setting | Value |
|---|---|
| Model | Qwen3-Coder-30B-A3B-Instruct, Ollama `qwen3-coder:30b` (Q4_K_M), weights blob `sha256:1194192cf2a187eb02722edcc3f77b11d21f537048ce04b67ccf8ba78863006a` |
| Served as | `qwen3-coder-128k` — `serving/Modelfile.qwen3-coder-128k` (`num_ctx 131072`) |
| Server | Ollama 0.34.4, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0` |
| Harness | `LEDGERBENCH_BACKEND=openai`, `LEDGERBENCH_SHOW_LAYOUT=1`, temperature 0.2, max tokens 8000, k = 4 |
| Hardware | Apple M5 Max Mac Studio, 36 GB unified memory, macOS 27.0 |
| Launcher | `scripts/run_campaign.sh` (sequential, skips completed arm/seed pairs) |
| Sequence | `tasks/` and `oracles/` byte-identical to freeze commit `257dc61` |

The seed is **not** passed to the model server, so seeds are independent
repeats; rerunning will not reproduce these logs exactly.

## Launcher logs — `logs/`

`campaign_before_reboot.log` and `campaign.log` are the launcher's
START/END/SKIP lines. The machine restarted unexpectedly at about 17:37 on
2026-09-25 during arm A seed 11; that partial run was deleted by the launcher
and rerun from scratch with the same seed (the only infrastructure rerun). The
campaign was also suspended (SIGSTOP) from 22:44 on 2026-09-27 to 00:39 on
2026-09-28, with no loss of state. `arm*_seed*.out` are each run's stdout;
`analyze.out` is the analysis output.

## Excluded attempts — `data/excluded/`

Not used for any reported number; kept so nothing is hidden.

| Archive | What it is | Why excluded |
|---|---|---|
| `runs_smoke.tar.xz` | 2-task smoke tests, without and with the layout flag | smoke tests |
| `runs_published_protocol.tar.xz` + `logs_published_protocol.tar.xz` | partial arm A seed 1 under the published protocol (no layout flag) | the agent wrote to a file the tests never import; protocol changed before the main campaign |
| `runs_truncated_32k.tar.xz` + `logs_truncated_32k.tar.xz` | partial arm A seed 1 at 32k context | server log showed prompts being truncated |
| `runs_64k.tar.xz` + `logs_64k.tar.xz` | arm A seeds 1–5 at 64k context | server log showed 2 truncated prompts in seed 1; later arms' prompts were growing |

## Regenerating every number

```bash
python -m harness.unpack_runs                 # verifies data/SHA256SUMS, extracts into runs/
python -m harness.analyze                     # results/metrics.csv, results/h1_events.csv (byte-identical)
python -m harness.paper_numbers --isolation   # leak + separation scans, then every paper number
```

`paper_numbers` writes `results/paper_numbers.json`, `results/claims.md`
(each claim, its value and its source) and `paper/numbers.tex` (the macros the
paper uses). `python -m harness.unpack_runs --excluded` also extracts the
excluded attempts.
