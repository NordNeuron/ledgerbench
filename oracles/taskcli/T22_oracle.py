from _helpers import run_cli


def test_search_matches_substring_anywhere_in_title():
    run_cli("add", "Grand unified theory")
    result = run_cli("search", "unified")
    assert result.returncode == 0, result.stderr
    assert "Grand unified theory" in result.stdout


def test_search_output_is_pipe_safe_and_iso_dated():
    # Cross-invariant probe: search inherits the global output rules - no
    # ANSI when piped (R12), ISO dates (R4).
    run_cli("add", "Search me dated", "--due", "2026-08-08")
    result = run_cli("search", "search me")
    assert result.returncode == 0, result.stderr
    line = next((l for l in result.stdout.splitlines() if "Search me dated" in l), None)
    assert line is not None
    assert "\x1b[" not in result.stdout
    if "2026" in line:
        assert "2026-08-08" in line, f"due date shown but not ISO: {line!r}"
