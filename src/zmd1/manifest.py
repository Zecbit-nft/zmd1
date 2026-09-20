"""The ZMD-1 item manifest: its hash, its signing digest, and its schema.

The manifest carries everything human-facing about an item. It travels
off-chain. What binds it to the chain is its BLAKE2b-256 content hash, carried
inside a full-form descriptor, and the creator's signature over a digest
computed here.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .canonical import canonicalize
from .errors import Invalid, SchemaUnavailable

ITEM_SIG_DOMAIN = b"ZMD1-ItemSig"
SCHEMA_VERSION = "zmd1"

SCHEMA_PATH = Path(__file__).parent / "schema" / "item-manifest.json"


@lru_cache(maxsize=1)
def schema() -> dict[str, Any]:
    """Return the normative JSON Schema shipped with this package."""
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        result: dict[str, Any] = json.load(handle)
    return result


def content_hash(manifest: Any) -> str:
    """Return BLAKE2b-256 of the canonical manifest bytes, as lowercase hex."""
    return hashlib.blake2b(canonicalize(manifest), digest_size=32).hexdigest()


def signing_digest(manifest: Any) -> str:
    """Return the digest a creator signs, as lowercase hex.

    The signature covers the manifest with ``creator.sig`` removed, because a
    signature cannot cover itself, and is domain-separated by
    ``ZMD1-ItemSig`` so it cannot be replayed as any other digest in the
    protocol.
    """
    if not isinstance(manifest, dict) or "creator" not in manifest:
        raise Invalid("manifest has no creator object")
    creator = manifest["creator"]
    if not isinstance(creator, dict):
        raise Invalid("manifest creator must be an object")

    unsigned = dict(manifest)
    unsigned["creator"] = {k: v for k, v in creator.items() if k != "sig"}
    return hashlib.blake2b(ITEM_SIG_DOMAIN + canonicalize(unsigned), digest_size=32).hexdigest()


def media_hash(data: bytes) -> str:
    """Return BLAKE2b-256 of media bytes, as lowercase hex."""
    return hashlib.blake2b(data, digest_size=32).hexdigest()


def validate_schema(manifest: Any) -> None:
    """Validate a manifest against the JSON Schema.

    Requires the optional ``jsonschema`` dependency::

        pip install "zmd1[schema]"

    Schema validation is a convenience, not the security boundary. A manifest
    can satisfy the schema and still fail :func:`zmd1.verify.verify`, which is
    the check that matters.
    """
    try:
        import jsonschema
    except ImportError as exc:
        raise SchemaUnavailable(
            'schema validation needs the optional dependency: pip install "zmd1[schema]"'
        ) from exc

    validator = jsonschema.Draft202012Validator(schema())
    errors = sorted(validator.iter_errors(manifest), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        location = "$" + "".join(f"[{p!r}]" for p in first.absolute_path)
        raise Invalid(f"manifest does not match the schema at {location}: {first.message}")
