import json

from taskcli import cli


def test_add_and_list(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    cli.main(["add", "Buy milk"])
    capsys.readouterr()
    cli.main(["list"])
    out = capsys.readouterr().out
    assert "Buy milk" in out
    assert "1" in out


def test_storage_file_contents(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.main(["add", "Write report"])
    data = json.loads((tmp_path / "tasks.json").read_text())
    assert data == [{"id": 1, "title": "Write report", "done": False}]


def test_done_and_delete(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    cli.main(["add", "Task A"])
    cli.main(["done", "1"])
    data = json.loads((tmp_path / "tasks.json").read_text())
    assert data[0]["done"] is True

    cli.main(["delete", "1"])
    data = json.loads((tmp_path / "tasks.json").read_text())
    assert data == []


def test_done_missing_id_exits_nonzero(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    try:
        cli.main(["done", "99"])
        assert False, "expected SystemExit"
    except SystemExit as e:
        assert e.code != 0
