from _helpers import run_cli


def test_list_shows_high_priority():
    run_cli("add", "Buy milk", "--priority", "high")
    result = run_cli("list")
    assert result.returncode == 0, result.stderr
    line = next(l for l in result.stdout.splitlines() if "Buy milk" in l)
    assert "high" in line


def test_list_shows_default_priority_med():
    run_cli("add", "Water the plants")
    result = run_cli("list")
    assert result.returncode == 0, result.stderr
    line = next(l for l in result.stdout.splitlines() if "Water the plants" in l)
    assert "med" in line
