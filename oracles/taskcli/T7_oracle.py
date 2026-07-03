from _helpers import run_cli


def test_stats_on_empty_project():
    result = run_cli("stats")
    assert result.returncode == 0, result.stderr
    assert "Total: 0" in result.stdout
    assert "Done: 0" in result.stdout
    assert "Open: 0" in result.stdout


def test_stats_after_mixed_activity():
    run_cli("add", "A", "--priority", "high")
    run_cli("add", "B", "--priority", "med")
    run_cli("add", "C", "--priority", "med")
    result = run_cli("stats")
    assert result.returncode == 0, result.stderr
    assert "Total: 3" in result.stdout
    assert "Priority high: 1" in result.stdout
    assert "Priority med: 2" in result.stdout
    assert "Priority low: 0" in result.stdout
