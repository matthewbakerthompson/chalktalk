"""
What someone meets first after `pip install chalktalk`: the command with
nothing after it, a typo, `chalk list`, and a package that carries the
designer and knows its own version. These hold those in place.
"""
import re
import sys
from importlib.resources import files
from pathlib import Path

import pytest

from chalktalk import DOCS_URL, __version__, cli
from chalktalk.designer import server as S

ROOT = Path(__file__).resolve().parent.parent


# ── the command line's front door ─────────────────────────────────────────────

def test_bare_chalk_says_what_it_is_and_where_to_start(capsys):
    assert cli.main([]) == 0
    out = capsys.readouterr().out
    assert out.startswith(f"chalktalk {__version__}:")
    assert "Start here" in out and "design" in out and DOCS_URL in out
    assert out.isascii() and max(len(line) for line in out.splitlines()) <= 80


def test_help_is_the_same_overview(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--help"])
    assert e.value.code == 0 and "Start here" in capsys.readouterr().out


def test_the_overview_lists_every_command_and_only_real_ones(capsys):
    cli.main([])
    listed = {m.group(1) for m in re.finditer(r"^  ([a-z]+)\b", capsys.readouterr().out, re.M)}
    assert listed == set(cli._COMMANDS)


def test_a_mistyped_command_gets_a_suggestion(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["desgin"])
    err = capsys.readouterr().err
    assert e.value.code == 2 and "Unknown command 'desgin'" in err and "design'?" in err


def test_chalk_list_on_its_own_lists_what_it_can_list(capsys):
    assert cli.main(["list"]) == 0
    out = capsys.readouterr().out
    assert all(kind in out for kind, _ in cli._LISTS)
    assert cli.main(["list", "widgets"]) == 1
    assert "Can't list 'widgets'" in capsys.readouterr().out


def test_a_mistyped_play_gets_the_nearest_name():
    with pytest.raises(SystemExit, match="Did you mean smash"):
        cli.main(["show", "smsh"])


def test_a_new_playbook_without_json_says_how(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as e:
        cli.main(["design", "week3", "--no-open"])
    assert "design week3.json" in str(e.value)


def test_json_can_be_left_off_a_file_that_exists(tmp_path, monkeypatch, capsys):
    from chalktalk.catalog import passing
    from chalktalk.models import Playbook
    Playbook(name="Week 3", plays=[passing.mesh_concept()]).save(str(tmp_path / "week3.json"))
    monkeypatch.chdir(tmp_path)
    assert cli.main(["check", "week3"]) == 0
    started = {}
    monkeypatch.setattr(S, "serve", lambda session, port, open_browser, quiet=False:
                        started.update(session=session))
    assert cli.main(["design", "week3", "--no-open"]) == 0
    assert started["session"].file == str(tmp_path / "week3.json")


@pytest.mark.parametrize("argv0, prog", [
    (r"C:\Python312\Scripts\chalk.exe", "chalk"),
    ("/usr/local/bin/chalk", "chalk"),
    ("/usr/local/bin/chalktalk", "chalktalk"),
    (r"C:\site-packages\chalktalk\__main__.py", "python -m chalktalk"),
])
def test_help_names_the_command_the_way_it_was_typed(monkeypatch, argv0, prog):
    monkeypatch.setattr(sys, "argv", [argv0])
    assert cli._prog_name() == prog


# ── the package ───────────────────────────────────────────────────────────────

def test_the_version_lives_in_one_place_and_the_changelog_has_it():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dynamic = ["version"]' in pyproject
    assert 'version = { attr = "chalktalk.__version__" }' in pyproject
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(rf"^## {re.escape(__version__)}$", changelog, re.M), \
        f"CHANGELOG.md needs a '## {__version__}' section before a release"


def test_the_designer_page_ships_inside_the_package():
    assert files("chalktalk").joinpath("designer", "app.html").is_file()
    assert 'chalktalk = ["designer/*.html"]' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_the_page_learns_its_version_and_docs_link_from_the_designer(tmp_path):
    page = S.Session(str(tmp_path)).page()
    assert f'"version":"{__version__}"' in page.replace(" ", "")
    assert DOCS_URL in page
