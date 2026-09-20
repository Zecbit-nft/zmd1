"""ZMD-1: a metadata standard for Zcash Shielded Assets.

See SPEC.md for the normative specification.
"""

from __future__ import annotations

from .canonical import canonicalize
from .cid import decode as decode_cid
from .cid import encode as encode_cid
from .descriptor import (
    Descriptor,
    Form,
    asset_desc_hash,
    build,
    parse,
)
from .errors import Invalid, NodeError, NodeUnreachable, SchemaUnavailable, Zmd1Error
from .manifest import content_hash, media_hash, schema, signing_digest, validate_schema
from .onchain import Node
from .verify import ChainContext, Result, verify

__version__ = "1.0.0"

__all__ = [
    "ChainContext",
    "Descriptor",
    "Form",
    "Invalid",
    "Node",
    "NodeError",
    "NodeUnreachable",
    "Result",
    "SchemaUnavailable",
    "Zmd1Error",
    "__version__",
    "asset_desc_hash",
    "build",
    "canonicalize",
    "content_hash",
    "decode_cid",
    "encode_cid",
    "media_hash",
    "parse",
    "schema",
    "signing_digest",
    "validate_schema",
    "verify",
]
