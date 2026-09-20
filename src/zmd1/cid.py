"""CIDv1 encoding for canonical manifest bytes.

ZMD-1 addresses manifests with a CIDv1 using the ``raw`` multicodec, so the
addressed block is exactly the canonical byte string and nothing wraps it.
Encoding is base32 lowercase without padding, multibase prefix ``b``.

The CID is a retrieval hint. The normative binding is the BLAKE2b-256 content
hash carried alongside it in the asset descriptor.
"""

from __future__ import annotations

import base64
import hashlib
from typing import NamedTuple

from .errors import Invalid

CID_VERSION = 0x01
CODEC_RAW = 0x55

MULTIHASH_SHA2_256 = 0x12
MULTIHASH_BLAKE2B_256 = 0xB220

_DIGESTS = {
    MULTIHASH_SHA2_256: lambda data: hashlib.sha256(data).digest(),
    MULTIHASH_BLAKE2B_256: lambda data: hashlib.blake2b(data, digest_size=32).digest(),
}


class DecodedCid(NamedTuple):
    """The parts of a CIDv1 relevant to ZMD-1."""

    version: int
    codec: int
    multihash_code: int
    digest: bytes


def _encode_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("varint must be non-negative")
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _decode_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if offset >= len(data):
            raise Invalid("truncated varint in CID")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
        if shift > 63:
            raise Invalid("varint too long in CID")


def _b32_encode(data: bytes) -> str:
    return base64.b32encode(data).decode("ascii").rstrip("=").lower()


def _b32_decode(text: str) -> bytes:
    padded = text.upper() + "=" * (-len(text) % 8)
    try:
        return base64.b32decode(padded)
    except Exception as exc:
        raise Invalid(f"CID is not valid base32: {exc}") from exc


def encode(data: bytes, multihash_code: int = MULTIHASH_SHA2_256) -> str:
    """Return the CIDv1 of ``data`` as a raw block."""
    digest_fn = _DIGESTS.get(multihash_code)
    if digest_fn is None:
        raise ValueError(f"unsupported multihash code {multihash_code:#x}")
    digest = digest_fn(data)
    body = (
        _encode_varint(CID_VERSION)
        + _encode_varint(CODEC_RAW)
        + _encode_varint(multihash_code)
        + _encode_varint(len(digest))
        + digest
    )
    return "b" + _b32_encode(body)


def decode(cid: str) -> DecodedCid:
    """Parse a base32 CIDv1 into its parts."""
    if not cid.startswith("b"):
        raise Invalid("CID must use the base32 multibase prefix 'b'")
    body = _b32_decode(cid[1:])
    version, offset = _decode_varint(body, 0)
    if version != CID_VERSION:
        raise Invalid(f"CID version {version} is not supported; ZMD-1 requires CIDv1")
    codec, offset = _decode_varint(body, offset)
    multihash_code, offset = _decode_varint(body, offset)
    length, offset = _decode_varint(body, offset)
    digest = body[offset:]
    if len(digest) != length:
        raise Invalid(f"CID declares a {length}-byte digest but carries {len(digest)}")
    return DecodedCid(version, codec, multihash_code, digest)


def matches(cid: str, data: bytes) -> bool:
    """Return whether ``cid`` addresses ``data``."""
    parsed = decode(cid)
    if parsed.codec != CODEC_RAW:
        return False
    digest_fn = _DIGESTS.get(parsed.multihash_code)
    if digest_fn is None:
        raise Invalid(f"unsupported multihash code {parsed.multihash_code:#x} in CID")
    return digest_fn(data) == parsed.digest
