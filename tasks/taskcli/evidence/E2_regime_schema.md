---
id: E2
task: T14
invalidates: {schema: tasks_table}
---

# E2 — Schema regime change: `tasks` table → `items` table (introduced at T14)

## What changed

Before T14, all task rows lived in a SQLite table named `tasks` (the
schema established by the T6 storage migration). At T14 the schema was
normalized for future multi-type records: the table is now named `items`
and carries an additional `kind` column ('task' for every current row).
The old `tasks` table must no longer exist in `tasks.db`.

The database file name (`tasks.db`) and every piece of CLI behavior are
unchanged. Only the internal schema moved.

## Why this matters for the ledger

Assertions written between T6 and T13 that probe the database directly
were written against the `tasks` table — see the
`assumes: {schema: tasks_table}` metadata on `T6_assert.py` and
`T10_assert.py`. The behaviors they protect (sqlite persistence, backup
correctness) still hold, but the probing method — `SELECT ... FROM tasks`
— targets a table that correctly no longer exists. A fully correct
post-T14 implementation fails those assertions on replay while passing
every CLI-level oracle.

Assertions that go through the CLI, or that probe the database file
without naming the `tasks` table, are unaffected.
