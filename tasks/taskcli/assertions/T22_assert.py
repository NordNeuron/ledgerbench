# LEDGER-META
# id: A22
# requirement: R22
# introduced_task: T22
# assumes: {}
# tier: correctness
from _helpers import run_cli


def test_search_finds_case_insensitive_match():
    run_cli("add", "Water the Ferns")
    run_cli("add", "File the taxes")
    result = run_cli("search", "ferns")
    assert result.returncode == 0, result.stderr
    assert "Water the Ferns" in result.stdout
    assert "File the taxes" not in result.stdout


def test_search_with_no_match_lists_nothing():
    run_cli("add", "Lonely entry")
    result = run_cli("search", "zzzquux")
    assert result.returncode == 0, result.stderr
    assert "Lonely entry" not in result.stdout
