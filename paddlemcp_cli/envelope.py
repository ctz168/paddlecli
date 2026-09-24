#!/usr/bin/env python3
"""Samai Command Envelope (SCE) v1 — quoting-proof command framing.

Python port of the Go implementation in samaidev/samcommand
(internal/envelope). Licensed MIT, same as this repository.

# The problem

When an AI agent remote-controls this CLI/server, the command text often
travels through layers that re-parse or "repair" text:

    agent → IM/chat gateway → HTTP POST → tunnel → server → kernel

Gateways routinely eat `"` characters, convert straight quotes to smart
quotes (“ ”), strip backslashes, re-wrap lines or convert line endings.
By the time the code reaches the kernel, quoting is destroyed and the
code either crashes or does something else entirely ("quoting hell").

# The idea

Wrap the code between two plain lowercase markers:

    samaicmdbegin
    v=1
    enc=b64url
    crc=1a2b3c4d
    <payload lines>
    samaicmdend

The markers are pure ASCII lowercase letters — nothing for a gateway to
mangle. The payload itself is base64url-encoded, so it contains ONLY
[A-Za-z0-9-_]: no quotes, no backslashes, no dollar signs, nothing that
any shell or gateway considers special. A CRC32 over the decoded payload
catches any residual corruption and tells the agent to retry.

enc=raw is also supported for transports that merely re-quote structure
but pass content through verbatim: the payload between the markers is
taken literally (CRLF normalised to LF), so no escaping of any kind is
needed. raw payloads must not contain a line consisting solely of the
end marker — use b64url for byte-exact or adversarial cases.

Whitespace inside a b64/b64url/hex payload (spaces, tabs, CR, LF) is
ignored during parsing, so gateways that re-wrap lines cannot corrupt it.
"""

import base64
import binascii
import re
import zlib

BEGIN_MARKER = "samaicmdbegin"
END_MARKER = "samaicmdend"

VERSION = "1"          # the only protocol version this parser understands
WRAP_WIDTH = 76        # encoder line width; parsers accept ANY wrapping
MAX_PAYLOAD_BYTES = 16 << 20   # 16 MiB decoded payload cap

ENC_RAW = "raw"        # payload is literal text between the markers
ENC_B64 = "b64"        # base64, alphabet auto-detected, whitespace-insensitive
ENC_B64URL = "b64url"  # base64, URL-safe alphabet (recommended)
ENC_HEX = "hex"        # lowercase hex (paranoid transports)


class EnvelopeError(ValueError):
    """Raised when a payload cannot be parsed from an envelope."""


def _split_lines(text: str):
    # split on \n and strip trailing \r (CRLF → LF)
    return text.replace("\r\n", "\n").split("\n")


def _is_marker_line(line: str, marker: str) -> bool:
    return line.strip() == marker


def _has_header(line: str, key: str) -> bool:
    # "key=value" for a KNOWN key only; unknown FOO=bar lines are payload
    return line.lstrip(" \t").startswith(key + "=")


def _header_value(line: str) -> str:
    return line[line.index("=") + 1:].strip()


def sniff(text: str) -> bool:
    """Cheap check: does this text look like it contains an envelope?"""
    return isinstance(text, str) and BEGIN_MARKER in text


def parse(text: str) -> bytes:
    """Extract and decode the first envelope found in *text*.

    Parsing rules (designed around what gateways do to text):
      - Begin/end markers must be alone on their line (surrounding
        whitespace tolerated). Text before begin / after end is ignored,
        so agents may paste the envelope inside a chat message.
      - Header block: consecutive lines directly after the begin marker
        that start with a KNOWN key (v=, enc=, crc=). Any other line —
        including blank lines and "FOO=bar"-lookalikes — starts the
        payload.
      - b64/b64url: all ASCII whitespace in the payload is stripped
        before decoding (re-wrapped lines are harmless). Padding is
        optional; both standard and URL-safe alphabets are accepted.
      - hex: whitespace stripped, must be valid hex.
      - raw: payload lines are joined with \\n (CRLF → LF), giving
        byte-identical text for everything except a lost trailing
        newline. If byte-exactness matters, use b64url.
    """
    if not isinstance(text, str):
        raise EnvelopeError("envelope: input must be str")
    lines = _split_lines(text)

    start = -1
    for i, ln in enumerate(lines):
        if _is_marker_line(ln, BEGIN_MARKER):
            start = i
            break
    if start < 0:
        raise EnvelopeError("envelope: no '%s' marker found" % BEGIN_MARKER)

    end = -1
    for i in range(start + 1, len(lines)):
        if _is_marker_line(lines[i], END_MARKER):
            end = i
            break
    if end < 0:
        raise EnvelopeError("envelope: no '%s' marker found" % END_MARKER)

    version, enc, crc = VERSION, ENC_B64URL, ""   # b64url is the default
    body_start = start + 1
    while body_start < end:
        ln = lines[body_start]
        if _has_header(ln, "v"):
            version = _header_value(ln)
            if version != VERSION:
                raise EnvelopeError("envelope: unsupported v= (only v=1): got %r" % version)
        elif _has_header(ln, "enc"):
            enc = _header_value(ln).lower()
        elif _has_header(ln, "crc"):
            crc = _header_value(ln).lower()
        else:
            break  # first non-header line: payload starts here
        body_start += 1

    body_lines = lines[body_start:end]
    if not body_lines or (len(body_lines) == 1 and body_lines[0].strip() == ""):
        raise EnvelopeError("envelope: empty payload")

    if enc == ENC_RAW:
        raw = "\n".join(body_lines)
        for ln in raw.split("\n"):
            if _is_marker_line(ln, END_MARKER):
                raise EnvelopeError(
                    "envelope: raw payload contains the end marker — re-send with enc=b64url")
        payload = raw.encode("utf-8")
    elif enc in (ENC_B64, ENC_B64URL, ENC_HEX):
        payload = _decode_body_text(enc, "\n".join(body_lines))
    else:
        raise EnvelopeError("envelope: unknown enc= (use raw | b64url | b64 | hex): got %r" % enc)

    if len(payload) > MAX_PAYLOAD_BYTES:
        raise EnvelopeError("envelope: payload too large: %d > %d bytes"
                            % (len(payload), MAX_PAYLOAD_BYTES))
    if crc:
        if crc32_hex(payload) != crc:
            raise EnvelopeError(
                "envelope: crc mismatch — payload corrupted in transit "
                "(want %s, got %s) — re-send with enc=b64url" % (crc, crc32_hex(payload)))
    return payload


def _decode_body_text(enc: str, text: str) -> bytes:
    # ignore ALL whitespace (gateways re-wrap lines; treating whitespace
    # as noise makes the payload immune), padding '=' is optional
    s = re.sub(r"[ \t\r\n\v\f]+", "", text)
    if not s:
        raise EnvelopeError("envelope: empty payload")
    if len(s) > MAX_PAYLOAD_BYTES * 2:   # rough guard before decoding
        raise EnvelopeError("envelope: payload too large: encoded length %d" % len(s))
    s = s.rstrip("=")
    try:
        if enc == ENC_HEX:
            return binascii.unhexlify(s.lower())
        if enc == ENC_B64URL:
            # URL-safe unless the payload actually contains standard chars
            if not re.search(r"[+/]", s):
                try:
                    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
                except (binascii.Error, ValueError):
                    pass
            return base64.b64decode(s + "=" * (-len(s) % 4))
        if enc == ENC_B64:
            # standard unless the payload actually contains URL-safe chars
            alpha = base64.urlsafe_b64decode if re.search(r"[-_]", s) else base64.b64decode
            return alpha(s + "=" * (-len(s) % 4))
    except (binascii.Error, ValueError) as e:
        raise EnvelopeError("envelope: payload decode failed (%s): %s" % (enc, e))
    raise EnvelopeError("envelope: unknown enc= (use raw | b64url | b64 | hex): got %r" % enc)


def crc32_hex(payload: bytes) -> str:
    return "%08x" % (zlib.crc32(payload) & 0xFFFFFFFF)


def encode_b64url(payload: bytes) -> str:
    """Build the canonical envelope (b64url mode: whitespace-immune, CRC'd)."""
    return _encode(payload, ENC_B64URL)


def encode_raw(payload: str) -> str:
    """Build an envelope whose payload is the literal code text.

    Refuses payloads containing a line equal to the end marker (impossible
    to frame) — callers should fall back to encode_b64url in that case.
    """
    for ln in payload.split("\n"):
        if _is_marker_line(ln, END_MARKER):
            raise EnvelopeError("envelope: raw payload contains the end marker")
    return _encode(payload.rstrip("\n").encode("utf-8"), ENC_RAW)


def _encode(payload: bytes, enc: str) -> str:
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise EnvelopeError("envelope: payload too large: %d > %d bytes"
                            % (len(payload), MAX_PAYLOAD_BYTES))
    out = [BEGIN_MARKER, "v=%s" % VERSION, "enc=%s" % enc, "crc=%s" % crc32_hex(payload)]
    if enc == ENC_RAW:
        out.append(payload.decode("utf-8"))
    elif enc == ENC_B64URL:
        s = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        out.extend(s[i:i + WRAP_WIDTH] for i in range(0, len(s), WRAP_WIDTH) or [""])
    else:
        raise EnvelopeError("envelope: encoder supports raw|b64url, got %r" % enc)
    out.append(END_MARKER)
    return "\n".join(out)


def decode_maybe_b64url(value: str):
    """Decode a b64url string that a respenc-armed server sent back.

    Returns None when *value* is not valid b64url (so callers can fall
    back to the plain-text field)."""
    if not value:
        return None
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode("utf-8", "replace")
    except (binascii.Error, ValueError):
        return None


# Text fields the server moves into *_b64 when ?respenc=b64url is armed.
RESPENC_FIELDS = ("stdout", "stderr", "error", "error_type", "traceback")


def decode_respenc(data: dict, plain: bool = False) -> dict:
    """Post-process a server response that came back with ?respenc=b64url.

    The respenc-armed server blanks the plain text fields and moves their
    content into ``*_b64`` (unpadded urlsafe base64url). What to do with
    that depends on who is reading:

    plain=False (default, agent mode):
        Return the dict UNCHANGED. The *_b64 fields stay byte-exact, so
        the printed JSON survives quote-mangling transports (IM gateways,
        chat bridges) on the way back to the agent, which decodes *_b64
        itself. This is the fix for "execution works but responses are
        unreliable": never re-expose decoded text to the return path.

    plain=True (human/debug mode):
        Decode *_b64 into the blanked plain fields and drop the *_b64
        keys, giving readable text. ONLY safe when the reader sees this
        text directly (local terminal) — through a chat bridge it can be
        mangled again. If a field fails to decode, its *_b64 value is
        kept as-is (visible and recoverable) instead of being silently
        emptied.
    """
    if not plain:
        return data
    for k in RESPENC_FIELDS:
        v = data.pop(k + "_b64", None)
        if v:
            decoded = decode_maybe_b64url(v)
            data[k] = decoded if decoded is not None else v
    return data
