#!/usr/bin/env python3
"""Integration tests for the Flask server (paddle_server.py).

Runs the real server app via Flask's test client — no network needed.
Skips the whole module when Flask is unavailable (e.g. minimal CI).

Run with:  python -m pytest tests/test_server.py -q
"""

import json
import os
import sys
import zlib
import base64

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import flask  # noqa: F401
    import psutil  # noqa: F401
except ImportError:
    flask = None

if flask is not None:
    import importlib.util

    _spec = importlib.util.spec_from_file_location(
        "paddle_server", os.path.join(os.path.dirname(__file__), "..", "paddle_server.py"))
    _srv = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_srv)

    def _client():
        _srv.app.config["TESTING"] = True
        return _srv.app.test_client()

    def _envelope(payload: bytes) -> str:
        pl = base64.urlsafe_b64encode(payload).decode().rstrip("=")
        crc = "%08x" % (zlib.crc32(payload) & 0xFFFFFFFF)
        return "samaicmdbegin\nv=1\nenc=b64url\ncrc=%s\n%s\nsamaicmdend" % (crc, pl)


def test_index_describes_server():
    if flask is None:
        print("SKIP (no flask)")
        return
    c = _client()
    r = c.get("/")
    data = r.get_json()
    assert data["name"] == "PaddleCLI Server"
    assert data["version"] == "2.1.4"
    assert "envelope" in data
    assert "/execute_stream" in data["endpoints"]


def test_health_ok():
    if flask is None:
        print("SKIP (no flask)")
        return
    data = _client().get("/health").get_json()
    assert data["status"] == "ok"
    assert "memory_available_gb" in data
    assert "gpu_available" in data


def test_execute_json_mode():
    if flask is None:
        print("SKIP (no flask)")
        return
    r = _client().post("/execute", json={"code": "print(40+2)", "timeout": 60})
    data = r.get_json()
    assert data["success"] is True
    assert data["stdout"] == "42\n"
    assert data["execution_time_sec"] >= 0


def test_execute_envelope_mode():
    if flask is None:
        print("SKIP (no flask)")
        return
    r = _client().post("/execute", data=_envelope("print('你好 AI Studio')".encode("utf-8")),
                       content_type="text/plain")
    data = r.get_json()
    assert data["success"] is True
    assert data["stdout"] == "你好 AI Studio\n"


def test_execute_envelope_crc_rejected():
    if flask is None:
        print("SKIP (no flask)")
        return
    env = _envelope(b"print(1)").replace("crc=", "crc=deadbeef\nx=", 1)
    # simpler: corrupt by replacing the crc line value
    lines = _envelope(b"print(1)").split("\n")
    lines[3] = "crc=00000000"
    bad = "\n".join(lines)
    r = _client().post("/execute", data=bad, content_type="text/plain")
    data = r.get_json()
    assert data["success"] is False
    assert "crc" in data["error"]


def test_execute_shell_command():
    if flask is None:
        print("SKIP (no flask)")
        return
    # mirror the real client path: !cmd is translated client-side
    # (RemoteExecutionEngine._prepare_code) before POSTing
    from paddlemcp_cli.executor import RemoteExecutionEngine
    code = RemoteExecutionEngine("http://localhost:5000")._prepare_code("!echo shell_ok")
    r = _client().post("/execute", json={"code": code, "timeout": 60})
    data = r.get_json()
    assert data["success"] is True
    assert "shell_ok" in data["stdout"]


def test_execute_error_propagation():
    if flask is None:
        print("SKIP (no flask)")
        return
    r = _client().post("/execute", json={"code": "1/0", "timeout": 60})
    data = r.get_json()
    assert data["success"] is False
    assert data["error_type"] == "ZeroDivisionError"
    assert "traceback" in data


def test_respenc_b64url_protection():
    if flask is None:
        print("SKIP (no flask)")
        return
    r = _client().post("/execute?respenc=b64url",
                       json={"code": "print('secret-output')", "timeout": 60})
    data = r.get_json()
    assert data["stdout"] == ""                       # plain field blanked
    decoded = base64.urlsafe_b64decode(
        data["stdout_b64"] + "=" * (-len(data["stdout_b64"]) % 4)).decode()
    assert decoded == "secret-output\n"               # *_b64 byte-exact


def test_status_and_history():
    if flask is None:
        print("SKIP (no flask)")
        return
    c = _client()
    c.post("/execute", json={"code": "print('for-history')", "timeout": 60})
    st = c.get("/status").get_json()
    assert st["status"] == "ok"
    assert st["current_directory"].startswith("/")
    hist = c.get("/history?limit=5").get_json()
    assert hist["total"] >= 1
    assert any("for-history" in h["command"] for h in hist["history"])


def test_variables_endpoint():
    if flask is None:
        print("SKIP (no flask)")
        return
    c = _client()
    c.post("/execute", json={"code": "my_var = [1, 2, 3]", "timeout": 60})
    data = c.get("/variables").get_json()
    assert "my_var" in data["variables"]
    assert data["variables"]["my_var"]["type"] == "list"
    assert data["variables"]["my_var"]["length"] == 3


def test_stream_sse():
    if flask is None:
        print("SKIP (no flask)")
        return
    r = _client().post("/execute_stream", json={"code": "print('sse-line')", "timeout": 60})
    body = r.get_data(as_text=True)
    assert "data: " in body
    assert "sse-line" in body


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
