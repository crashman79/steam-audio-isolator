#!/usr/bin/env python3
"""Tolerant parsing for ``pw-dump`` JSON output.

Older libpipewire versions (e.g. 1.2.7 shipped with the
``org.freedesktop.Platform`` 24.08 runtime) do not know every param type a
newer host PipeWire daemon can advertise. When that happens ``pw-dump`` emits
object entries *without a key*, producing invalid JSON:

    "Tag": [ ... ],
    [ ],
    [ { "id-00000060": null } ]

The missing keys are optional ``params`` details that this application does
not use, but the broken JSON makes the whole graph unparseable, which leaves
the UI with no sources and no destinations.

``loads_pw_dump`` transparently repairs those entries with synthetic keys so
the rest of the object graph can still be parsed.
"""

import json
import logging
from typing import Any, List, Tuple

logger = logging.getLogger(__name__)

_warned_about_repair = False


def _repair_missing_keys(text: str) -> Tuple[str, int]:
    """Insert synthetic keys where ``pw-dump`` omitted an object key.

    Returns the repaired text and the number of keys that were inserted.
    """
    out: List[str] = []
    stack: List[str] = []  # 'o' for object, 'a' for array
    expect_key = False
    inserted = 0
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        if ch in ' \t\r\n':
            out.append(ch)
            i += 1
            continue

        if ch == '"':
            # Copy a complete string literal (including escapes) verbatim.
            j = i + 1
            while j < n:
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            out.append(text[i:j])
            i = j
            if stack and stack[-1] == 'o' and expect_key:
                expect_key = False  # this string was an object key
            continue

        if ch == '{':
            if stack and stack[-1] == 'o' and expect_key:
                out.append(f'"__unknown{inserted}": ')
                inserted += 1
                expect_key = False
            stack.append('o')
            out.append(ch)
            i += 1
            expect_key = True
            continue

        if ch == '[':
            if stack and stack[-1] == 'o' and expect_key:
                out.append(f'"__unknown{inserted}": ')
                inserted += 1
                expect_key = False
            stack.append('a')
            out.append(ch)
            i += 1
            expect_key = False
            continue

        if ch in '}]':
            if stack:
                stack.pop()
            out.append(ch)
            i += 1
            expect_key = bool(stack) and stack[-1] == 'o'
            continue

        if ch == ':':
            out.append(ch)
            i += 1
            expect_key = False
            continue

        if ch == ',':
            out.append(ch)
            i += 1
            expect_key = bool(stack) and stack[-1] == 'o'
            continue

        # Bare scalar (number, true, false, null) at key position: same repair.
        if stack and stack[-1] == 'o' and expect_key:
            out.append(f'"__unknown{inserted}": ')
            inserted += 1
            expect_key = False
        out.append(ch)
        i += 1

    return ''.join(out), inserted


def loads_pw_dump(text: str) -> List[Any]:
    """Parse ``pw-dump`` output, repairing unkeyed entries if needed."""
    global _warned_about_repair
    if not text:
        return []
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        repaired, inserted = _repair_missing_keys(text)
        if not inserted:
            raise
        if not _warned_about_repair:
            _warned_about_repair = True
            logger.warning(
                "pw-dump emitted invalid JSON (%s); recovered %d unkeyed param entries "
                "(further repairs will be silent)",
                exc,
                inserted,
            )
        return json.loads(repaired)
