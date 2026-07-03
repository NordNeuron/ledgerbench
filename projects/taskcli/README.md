# taskcli

A minimal command-line task manager.

## Commands

- `python -m taskcli add <title>` — add a new task. Prints the assigned id.
- `python -m taskcli list` — list all tasks, in insertion order, showing id,
  done status, and title.
- `python -m taskcli done <id>` — mark the task with the given integer id as
  done.
- `python -m taskcli delete <id>` — delete the task with the given integer id.

Commands that reference an id exit with a non-zero status and an error
message on stderr if no task with that id exists.

## Storage format

Tasks are stored in a file named `tasks.json` in the current working
directory. If the file does not exist, the task list is treated as empty.

`tasks.json` is a JSON array of task objects. Each task object has:

- `id` (integer) — unique, assigned automatically as one more than the
  current maximum id (starts at 1).
- `title` (string) — the task title.
- `done` (boolean) — whether the task has been marked done.

Example:

```json
[
  {"id": 1, "title": "Buy milk", "done": false},
  {"id": 2, "title": "Write report", "done": true}
]
```
