import os

from _helpers import run_cli, workspace_path


def _write_config(text):
    with open(os.path.join(workspace_path(), "config.toml"), "w", encoding="utf-8") as f:
        f.write(text)


def test_config_today_pins_the_date():
    _write_config('today = "2026-06-15"\n')
    run_cli("add", "Yesterday news", "--due", "2026-06-14")
    result = run_cli("list", "--overdue")
    assert result.returncode == 0, result.stderr
    assert "Yesterday news" in result.stdout


def test_missing_config_keeps_default_behavior():
    cfg = os.path.join(workspace_path(), "config.toml")
    if os.path.exists(cfg):
        os.remove(cfg)
    result = run_cli("add", "No config needed")
    assert result.returncode == 0, result.stderr
    assert "No config needed" in run_cli("list").stdout
