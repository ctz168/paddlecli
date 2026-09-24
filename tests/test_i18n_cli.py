#!/usr/bin/env python3
"""Unit tests for i18n and CLI basics (paddlemcp_cli).

Run with:  python -m pytest tests/test_i18n_cli.py -q
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from paddlemcp_cli import i18n  # noqa: E402
from paddlemcp_cli import __version__  # noqa: E402


def test_version():
    assert __version__ == "2.1.1"
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:
        tomllib = None
    root = Path(__file__).resolve().parent.parent
    if tomllib is not None:
        with open(root / "pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
        assert pyproject["project"]["version"] == __version__
    # server version must match too (single source of truth policy)
    server = (root / "paddle_server.py").read_text(encoding="utf-8")
    assert '"version": "%s"' % __version__ in server


def test_default_lang_en():
    i18n.set_lang("en")
    assert i18n.get_lang() == "en"
    assert i18n.t("loading_notebook", name="x.ipynb") == "📖 Loading notebook: x.ipynb"


def test_switch_to_zh_and_back():
    i18n.set_lang("zh")
    assert i18n.get_lang() == "zh"
    assert i18n.t("loading_notebook", name="x.ipynb") == "📖 正在加载笔记本: x.ipynb"
    i18n.set_lang("en")


def test_fallback_to_key():
    i18n.set_lang("en")
    assert i18n.t("definitely_not_a_key") == "definitely_not_a_key"


def test_env_var_respected(monkeypatch):
    monkeypatch.setenv("PADDLECLI_LANG", "zh")
    import importlib
    mod = importlib.reload(i18n)
    assert mod.get_lang() == "zh"
    monkeypatch.setenv("PADDLECLI_LANG", "en")
    importlib.reload(i18n)


def test_all_keys_have_both_languages():
    en = set(i18n.TRANSLATIONS["en"].keys())
    zh = set(i18n.TRANSLATIONS["zh"].keys())
    assert en == zh, "en/zh key mismatch: %s" % (en ^ zh)


def test_cli_help_runs():
    from click.testing import CliRunner
    from paddlemcp_cli.cli import main
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output and "stream" in result.output and "exec" in result.output


def test_cli_version_flag():
    from click.testing import CliRunner
    from paddlemcp_cli.cli import main
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "2.1.1" in result.output


def test_cli_info_on_demo():
    from click.testing import CliRunner
    from paddlemcp_cli.cli import main
    demo = Path(__file__).resolve().parent / "demo.ipynb"
    runner = CliRunner()
    result = runner.invoke(main, ["info", str(demo)])
    assert result.exit_code == 0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print("PASS", fn.__name__)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FAIL", fn.__name__, e)
    print("ALL %d TESTS, %d FAILED" % (len(fns), failed))
    sys.exit(1 if failed else 0)
