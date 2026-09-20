"""RFC 8785 JSON canonicalization, over the subset ZMD-1 permits.

Object keys are sorted by UTF-16 code unit, insignificant whitespace is
removed, and every number must be an integer representable in 53 bits.

The integer restriction is part of ZMD-1 rather than of RFC 8785. It removes
the floating-point serialization problem instead of solving it: a manifest that
two implementations could serialize differently is rejected rather than allowed
to produce a silent hash mismatch.
"""

from __future__ import annotations

import json
from typing import Any

from .errors import Invalid

MAX_SAFE_INTEGER = 2**53 - 1


def _sort_key(key: str) -> bytes:
    return key.encode("utf-16-be")


def _string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _emit(node: Any, out: list[str], path: str) -> None:
    if isinstance(node, bool):
        out.append("true" if node else "false")
    elif node is None:
        out.append("null")
    elif isinstance(node, int):
        if abs(node) > MAX_SAFE_INTEGER:
            raise Invalid(f"{path}: integer exceeds 53 bits")
        out.append(str(node))
    elif isinstance(node, str):
        out.append(_string(node))
    elif isinstance(node, dict):
        out.append("{")
        for i, key in enumerate(sorted(node, key=_sort_key)):
            if not isinstance(key, str):
                raise Invalid(f"{path}: object keys must be strings")
            if i:
                out.append(",")
            out.append(_string(key))
            out.append(":")
            _emit(node[key], out, f"{path}.{key}")
        out.append("}")
    elif isinstance(node, (list, tuple)):
        out.append("[")
        for i, item in enumerate(node):
            if i:
                out.append(",")
            _emit(item, out, f"{path}[{i}]")
        out.append("]")
    else:
        raise Invalid(
            f"{path}: {type(node).__name__} is not permitted; "
            "fractional values must be expressed as strings"
        )


def canonicalize(document: Any) -> bytes:
    """Return the canonical UTF-8 serialization of a JSON document."""
    out: list[str] = []
    _emit(document, out, "$")
    return "".join(out).encode("utf-8")


def loads(data: bytes | str) -> Any:
    """Parse JSON, rejecting anything this module cannot canonicalize."""
    try:
        document = json.loads(data)
    except (ValueError, UnicodeDecodeError) as exc:
        raise Invalid(f"not valid JSON: {exc}") from exc
    canonicalize(document)
    return document
