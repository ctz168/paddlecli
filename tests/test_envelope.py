#!/usr/bin/env python3
"""Unit tests for the Samai Command Envelope module (paddlemcp_cli.envelope).

Run with:  python -m pytest tests/test_envelope.py -q
(plain stdlib fallback: python tests/test_envelope.py)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from paddlemcp_cli import envelope as E   # noqa: E402

SAMPLE = '''print("你好, world")
x = it's fine
!echo "shell quotes" > f.txt
'''


def test_roundtrip_b64url():
    env = E.encode_b64url(SAMPLE.encode("utf-8"))
    assert E.sniff(env)
    assert E.parse(env).decode("utf-8") == SAMPLE
    # canonical shape: 6 fixed lines for a payload that wraps to 1 line
    lines = env.split("\n")
    assert lines[0] == "samaicmdbegin" and lines[-1] == "samaicmdend"
    assert lines[1] == "v=1" and lines[2] == "enc=b64url"
    assert lines[3].startswith("crc=") and len(lines[3]) == 12


def test_payload_has_no_quotes():
    env = E.encode_b64url(SAMPLE.encode("utf-8"))
    body = "\n".join(env.split("\n")[4:-1])
    # \n between wrapped lines is expected (parsers strip whitespace);
    # no quoting-special char may appear as a payload CHARACTER
    for ch in "\"'`$\\;&|":
        assert ch not in body, "forbidden char %r leaked into payload" % ch


def test_crc_rejects_corruption():
    env = E.encode_b64url(SAMPLE.encode("utf-8"))
    lines = env.split("\n")
    lines[4] = lines[4].replace("A", "B", 1) if "A" in lines[4] else lines[4][:-1] + ("A" if lines[4][-1] != "A" else "C")
    corrupt = "\n".join(lines)
    try:
        E.parse(corrupt)
        # only passes if the tweak was a no-op; force-fail then
        assert corrupt == env, "corrupted envelope parsed without error"
    except E.EnvelopeError as e:
        assert "crc mismatch" in str(e)


def test_whitespace_and_rewrapping_tolerated():
    env = E.encode_b64url(SAMPLE.encode("utf-8"))
    # a gateway re-wraps the payload: every 7 chars, joined with spaces+CRLF
    lines = env.split("\n")
    body = "".join(lines[4:-1])
    rewrapped = "\r\n".join(body[i:i + 7] for i in range(0, len(body), 7))
    mangled = "\n".join(lines[:4] + [rewrapped] + lines[-1:])
    assert E.parse(mangled).decode("utf-8") == SAMPLE


def test_raw_mode():
    env = E.encode_raw(SAMPLE)
    assert "enc=raw" in env
    # by design (same as the Go original): raw mode loses a trailing newline
    assert E.parse(env).decode("utf-8") == SAMPLE.rstrip("\n")


def test_raw_mode_refuses_end_marker_line():
    try:
        E.encode_raw("ok\nsamaicmdend\n")
        assert False, "should have refused"
    except E.EnvelopeError:
        pass


def test_text_before_and_after_markers_ignored():
    env = E.encode_b64url(SAMPLE.encode("utf-8"))
    pasted = "Sure, here you go:\n%s\nHope that helps!" % env
    assert E.parse(pasted).decode("utf-8") == SAMPLE


def test_padding_optional_and_standard_alphabet_accepted():
    import base64
    std = base64.b64encode(SAMPLE.encode("utf-8")).decode()  # +/= alphabet, padded
    env = "samaicmdbegin\nv=1\nenc=b64url\ncrc=%s\n%s\nsamaicmdend" % (
        E.crc32_hex(SAMPLE.encode("utf-8")), std)
    assert E.parse(env).decode("utf-8") == SAMPLE


def test_hex_mode():
    env = ("samaicmdbegin\nv=1\nenc=hex\ncrc=%s\n%s\nsamaicmdend"
           % (E.crc32_hex(SAMPLE.encode()), SAMPLE.encode().hex()))
    assert E.parse(env).decode("utf-8") == SAMPLE


def test_bad_version_rejected():
    env = E.encode_b64url(b"hi").replace("v=1", "v=2")
    try:
        E.parse(env)
        assert False
    except E.EnvelopeError as e:
        assert "v=" in str(e)


def test_missing_crc_ok_but_bad_crc_rejected():
    # no crc header: parse succeeds (CRC is optional)
    payload = "print(1)\n"
    import base64
    b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    env = "samaicmdbegin\nv=1\nenc=b64url\n%s\nsamaicmdend" % b64
    assert E.parse(env).decode() == payload
    # wrong crc: rejected
    env_bad = env.replace("enc=b64url", "enc=b64url\ncrc=deadbeef")
    try:
        E.parse(env_bad)
        assert False
    except E.EnvelopeError as e:
        assert "crc mismatch" in str(e)


def test_unknown_headers_are_payload_not_headers():
    # a raw payload whose first line looks like KEY=VALUE must survive
    code = "FOO=bar\nprint(FOO)"
    env = E.encode_raw(code)
    assert E.parse(env).decode() == code


def test_no_envelope_raises():
    try:
        E.parse("print('plain code, no envelope')")
        assert False
    except E.EnvelopeError as e:
        assert "no 'samaicmdbegin'" in str(e)


def test_decode_maybe_b64url_fallback():
    assert E.decode_maybe_b64url("") is None
    assert E.decode_maybe_b64url("not valid b64url !!!") is None
    assert E.decode_maybe_b64url("aGVsbG8=") == "hello"


def test_decode_respenc_agent_mode_untouched():
    # v2.1.0 fix: default (agent) mode must return the respenc-armed
    # response VERBATIM — *_b64 fields stay byte-exact for the return path
    data = {"success": True, "stdout": "", "stdout_b64": "aGVsbG8=",
            "stderr": "", "execution_time_sec": 0.1}
    out = E.decode_respenc(dict(data), plain=False)
    assert out == data, "agent mode must not touch the response"
    assert out["stdout_b64"] == "aGVsbG8="
    assert out["stdout"] == ""


def test_decode_respenc_plain_mode_decodes_and_pops():
    import base64
    def b64(s):
        return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")
    data = {"success": True, "stdout": "", "stdout_b64": b64("hello"),
            "stderr": "", "stderr_b64": b64("warn\n"),
            "error": "", "error_b64": b64('say "hi" \\ o/')}
    out = E.decode_respenc(data, plain=True)
    assert out["stdout"] == "hello"
    assert out["stderr"] == "warn\n"
    assert out["error"] == 'say "hi" \\ o/'
    assert "stdout_b64" not in out and "stderr_b64" not in out and "error_b64" not in out


def test_decode_respenc_plain_mode_no_silent_loss():
    # undecodable *_b64 must be KEPT, never silently emptied (old bug:
    # decode_maybe_b64url(v) or "" turned failures into missing output)
    data = {"success": True, "stdout": "", "stdout_b64": "!!!not-b64url!!!"}
    out = E.decode_respenc(data, plain=True)
    assert out["stdout"] == "!!!not-b64url!!!"


def test_decode_respenc_plain_mode_empty_fields_untouched():
    # absent *_b64 (e.g. empty stdout, old server without respenc) → no-op
    data = {"success": False, "stdout": "kept", "variables": ["x"]}
    out = E.decode_respenc(dict(data), plain=True)
    assert out == data


def test_decode_respenc_roundtrip_with_server_semantics():
    # simulate the full server respenc move: blank plain, add *_b64
    import base64
    text = 'print("你好")\nback\\slash'
    b64 = base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")
    server_resp = {"success": True, "stdout": "", "stdout_b64": b64}
    agent_view = E.decode_respenc(dict(server_resp), plain=False)
    assert agent_view == server_resp                       # agent: byte-exact
    human_view = E.decode_respenc(dict(server_resp), plain=True)
    assert human_view["stdout"] == text                    # human: readable


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("PASS", fn.__name__)
    print("ALL %d TESTS PASSED" % len(fns))
