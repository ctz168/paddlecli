#!/usr/bin/env python3
"""Unit tests for the notebook parser (paddlemcp_cli.notebook).

Run with:  python -m pytest tests/test_notebook.py -q
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from paddlemcp_cli.notebook import (  # noqa: E402
    NotebookParser, Notebook, NotebookCell, CellType, parse_notebook,
)


def _write_nb(tmp_path, cells):
    nb = {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p = tmp_path / "sample.ipynb"
    p.write_text(json.dumps(nb, ensure_ascii=False), encoding="utf-8")
    return p


def test_parse_basic(tmp_path):
    p = _write_nb(tmp_path, [
        {"cell_type": "markdown", "metadata": {}, "source": ["# Title"]},
        {"cell_type": "code", "metadata": {}, "source": ["print(1)\n", "print(2)"],
         "execution_count": 1, "outputs": []},
        {"cell_type": "raw", "metadata": {}, "source": "raw text"},
    ])
    nb = NotebookParser.parse_file(str(p))
    assert len(nb.cells) == 3
    assert len(nb.code_cells) == 1
    assert len(nb.markdown_cells) == 1
    # list source joined, trailing newline stripped
    assert nb.code_cells[0].source == "print(1)\nprint(2)"
    assert nb.code_cells[0].is_code
    assert nb.cells[2].is_raw


def test_parse_string_source(tmp_path):
    p = _write_nb(tmp_path, [
        {"cell_type": "code", "metadata": {}, "source": "x = '你好'\n"},
    ])
    nb = NotebookParser.parse_file(str(p))
    assert nb.code_cells[0].source == "x = '你好'"   # trailing \n stripped


def test_magic_detection(tmp_path):
    p = _write_nb(tmp_path, [
        {"cell_type": "code", "metadata": {}, "source": "%cd /home/aistudio\n!ls -la"},
    ])
    nb = NotebookParser.parse_file(str(p))
    cell = nb.code_cells[0]
    assert cell.has_magic_commands()
    kinds = [k for k, _ in cell.get_magic_commands()]
    assert kinds == ["line", "shell"]


def test_tags(tmp_path):
    p = _write_nb(tmp_path, [
        {"cell_type": "code", "metadata": {"tags": ["train"]}, "source": "a=1"},
        {"cell_type": "code", "metadata": {}, "source": "b=2"},
    ])
    nb = NotebookParser.parse_file(str(p))
    tagged = nb.get_code_cells_by_tag("train")
    assert len(tagged) == 1 and tagged[0].source == "a=1"


def test_extract_code(tmp_path):
    p = _write_nb(tmp_path, [
        {"cell_type": "markdown", "metadata": {}, "source": "## Note"},
        {"cell_type": "code", "metadata": {}, "source": "print('hi')"},
    ])
    nb = NotebookParser.parse_file(str(p))
    code = NotebookParser.extract_code(nb, skip_markdown=False)
    assert "print('hi')" in code
    assert "# ## Note" in code


def test_missing_file_raises():
    try:
        NotebookParser.parse_file("/nonexistent/nope.ipynb")
        assert False, "should raise FileNotFoundError"
    except FileNotFoundError:
        pass


def test_wrong_suffix_raises(tmp_path):
    p = tmp_path / "notanotebook.txt"
    p.write_text("hello")
    try:
        NotebookParser.parse_file(str(p))
        assert False, "should raise ValueError"
    except ValueError:
        pass


def test_parse_dict_in_memory():
    nb = NotebookParser.parse_dict({"cells": [], "metadata": {}})
    assert isinstance(nb, Notebook)
    assert nb.cells == []


if __name__ == "__main__":
    import tempfile
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            import inspect
            sig = inspect.signature(fn)
            if "tmp_path" in sig.parameters:
                with tempfile.TemporaryDirectory() as td:
                    fn(td)
            else:
                fn()
            print("PASS", fn.__name__)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FAIL", fn.__name__, e)
    print("ALL %d TESTS, %d FAILED" % (len(fns), failed))
    sys.exit(1 if failed else 0)
