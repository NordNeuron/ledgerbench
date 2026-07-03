# LEDGER-META
# id: A16
# requirement: R16
# introduced_task: T16
# assumes: {}
# tier: correctness
from _helpers import run_cli


def test_tag_filter_shows_only_tagged_tasks():
    run_cli("add", "Work item", "--tag", "work")
    run_cli("add", "Home item", "--tag", "home")
    run_cli("add", "Untagged item")
    result = run_cli("list", "--tag", "work")
    assert result.returncode == 0, result.stderr
    assert "Work item" in result.stdout
    assert "Home item" not in result.stdout
    assert "Untagged item" not in result.stdout


def test_multiple_tags_round_trip():
    run_cli("add", "Dual purpose", "--tag", "work", "--tag", "urgent")
    for tag in ("work", "urgent"):
        result = run_cli("list", "--tag", tag)
        assert "Dual purpose" in result.stdout, f"missing under tag {tag}"
