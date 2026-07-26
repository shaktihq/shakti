from shakti.__about__ import __version__
from shakti.cli.main import main

EXPECTED_FILES = [
    "app/__init__.py",
    "app/main.py",
    "config/settings.yaml",
    "config/settings.production.yaml",
    "tests/test_app.py",
    "conftest.py",
    ".env",
    ".gitignore",
    "README.md",
    "requirements.txt",
]


def test_new_scaffolds_project(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["new", "demo_app"]) == 0
    root = tmp_path / "demo_app"
    for relative in EXPECTED_FILES:
        assert (root / relative).is_file(), relative
    main_py = (root / "app/main.py").read_text(encoding="utf-8")
    assert 'Shakti(title="demo_app"' in main_py
    assert "Created project" in capsys.readouterr().out


def test_new_refuses_existing_directory(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "taken").mkdir()
    assert main(["new", "taken"]) == 1
    assert "already exists" in capsys.readouterr().err


def test_new_rejects_invalid_name(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["new", "1bad"]) == 1
    assert "invalid project name" in capsys.readouterr().err


def test_version(capsys) -> None:
    assert main(["version"]) == 0
    assert __version__ in capsys.readouterr().out


def test_no_command_prints_help(capsys) -> None:
    assert main([]) == 1
    assert "shakti" in capsys.readouterr().out
