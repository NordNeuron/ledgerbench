from _helpers import run_cli


def test_errors_are_informative():
    result = run_cli("done", "31337")
    assert result.returncode != 0
    assert "31337" in result.stderr


def test_help_covers_all_commands():
    result = run_cli("--help")
    assert result.returncode == 0
    for cmd in ("add", "list", "done", "delete", "export"):
        assert cmd in result.stdout, f"--help does not mention {cmd}"
