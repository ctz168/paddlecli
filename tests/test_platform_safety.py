#!/usr/bin/env python3
"""Platform-safety regression tests (v2.1.6).

AI Studio aborts any notebook cell whose source contains a literal import of a
certain deep-learning framework (compat banner + SystemExit(1)).  In v2.1.5 and
earlier the embedded server source tripped this inside the %%writefile cell, so
paddle_server.py was never written on the platform and Flask looped forever.
These tests pin the invariant: NO banned token in the server file nor in any
cell of the shipped notebooks, and the embedded source stays in sync with disk.

Run with:  python -m pytest tests/test_platform_safety.py -q
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ROOT = os.path.join(os.path.dirname(__file__), "..")
# assembled at runtime so this very test file stays token-free as well
BANNED = "".join(("tor", "ch"))


def _server_src():
    with open(os.path.join(ROOT, "paddle_server.py"), encoding="utf-8") as f:
        return f.read()


def _nb_cells(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        nb = json.load(f)
    return ["".join(c.get("source", [])) for c in nb["cells"]]


def test_server_source_has_no_banned_token():
    src = _server_src()
    assert BANNED not in src, (
        "paddle_server.py contains the banned framework token — the AI Studio "
        "cell scanner would abort the %%writefile cell that embeds it"
    )


def test_both_notebooks_have_no_banned_token():
    for name in ("paddle_server.ipynb", "paddlecli.ipynb"):
        for i, cell in enumerate(_nb_cells(name)):
            assert BANNED not in cell, (
                "%s cell #%d contains the banned framework token" % (name, i)
            )


def test_writefile_cells_match_disk_server():
    disk = _server_src()
    for name, idx in (("paddle_server.ipynb", 4), ("paddlecli.ipynb", 1)):
        cells = _nb_cells(name)
        wf = cells[idx]
        assert wf.startswith("%%writefile paddle_server.py\n"), name
        embedded = wf[len("%%writefile paddle_server.py\n"):]
        assert embedded == disk, "%s embedded server source is out of sync" % name


def test_server_versions_consistent():
    src = _server_src()
    assert '"version": "2.1.6"' in src
    assert "version='2.1.6'" in src


def _cleanup_client():
    try:
        import flask  # noqa: F401
        import psutil  # noqa: F401
    except ImportError:
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "paddle_server", os.path.join(ROOT, "paddle_server.py"))
    srv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(srv)
    srv.app.config["TESTING"] = True
    return srv.app.test_client()


def test_cleanup_route_works_without_banned_probe():
    c = _cleanup_client()
    if c is None:
        print("SKIP (no flask)")
        return
    r = c.post("/cleanup")
    data = r.get_json()
    assert data["success"] is True
    assert "memory_available_gb" in data
