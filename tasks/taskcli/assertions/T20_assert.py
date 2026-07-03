# LEDGER-META
# id: A20
# requirement: R20
# introduced_task: T20
# assumes: {config: toml}
# tier: correctness
import os

from _helpers import run_cli, workspace_path


def _write_config(text):
    with open(os.path.join(workspace_path(), "config.toml"), "w", encoding="utf-8") as f:
        f.write(text)


def test_config_today_drives_overdue():
    _write_config('today = "2026-06-15"\n')
    run_cli("add", "Past thing", "--due", "2026-01-01")
    run_cli("add", "Future thing", "--due", "2026-12-01")
    result = run_cli("list", "--overdue")
    assert result.returncode == 0, result.stderr
    assert "Past thing" in result.stdout
    assert "Future thing" not in result.stdout


def test_config_default_priority_used_by_add():
    _write_config('default_priority = "high"\n')
    run_cli("add", "Important by default")
    _write_config("")
    run_cli("add", "Explicitly low", "--priority", "low")
    # In the priority-sorted view, a task added under default_priority=high
    # must rank above an explicitly low one.
    lines = run_cli("list", "--sort", "priority").stdout.splitlines()
    pos_high = next(i for i, l in enumerate(lines) if "Important by default" in l)
    pos_low = next(i for i, l in enumerate(lines) if "Explicitly low" in l)
    assert pos_high < pos_low, "config default_priority not honored by add"


def test_config_today_beats_env_var():
    _write_config('today = "2026-06-15"\n')
    run_cli("add", "Borderline", "--due", "2026-06-10")
    result = run_cli("list", "--overdue", env={"TASKCLI_TODAY": "2026-01-01"})
    assert "Borderline" in result.stdout, (
        "config.toml today must take precedence over the deprecated env var")
