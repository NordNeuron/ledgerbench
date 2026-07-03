---
id: E3
task: T20
invalidates: {config: env_vars}
---

# E3 — Configuration regime change: TASKCLI_* env vars → config.toml (introduced at T20)

## What changed

Before T20, the only configuration mechanism was the `TASKCLI_TODAY`
environment variable (introduced with T5's overdue feature as the test
hook for pinning "today"). At T20, configuration moved to an optional
`config.toml` in the working directory (`today` and `default_priority`
keys). The environment variable is **deprecated**: config.toml is the
supported mechanism and wins when both are present.

## Why this differs from E1/E2 (merely-obsolete, not contradictory)

Deprecation is not prohibition. Nothing in T20 forbids an implementation
from *still reading* `TASKCLI_TODAY` when no config file is present — it
is merely no longer the supported interface. An assertion that pins
"today" via the environment variable (see `assumes: {config: env_vars}`
on `T5_assert.py`) can therefore still be satisfied by vestigial
env-var-reading code. The question this regime change poses to a ledger
is quieter than E1/E2's hard contradiction: does the system keep carrying
(and coercing implementations to carry) dead-regime code that exists only
to satisfy assertions probing a deprecated mechanism?

Post-T20 commits that still read `TASKCLI_TODAY` are counted as
vestigial-code events by the analyzer.
