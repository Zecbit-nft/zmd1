"""The ZMD-1 asset descriptor: its grammar, its two forms, and its hash.

An asset's on-chain identity under ZIP 227 is the pair ``(ik, assetDescHash)``,
where ``ik`` is the issuance validating key and ``assetDescHash`` is a
personalized BLAKE2b-256 hash of an issuer-chosen byte string. Only the hash is
recorded on chain.

ZMD-1 defines what that byte string contains.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum

from .errors import Invalid

ASSET_DESC_PERSONAL = b"ZSA-AssetDescCRH"

TAG = "zmd1"
SEPARATOR = "|"
MAX_ASSET_DESC_BYTES = 256
MAX_INDEX = 0xFFFFFFFF

SLUG_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9]|-(?!-)){0,62}[a-z0-9]$|^[a-z0-9]$")
INDEX_PATTERN = re.compile(r"^(0|[1-9][0-9]{0,9})$")
CID_PATTERN = re.compile(r"^b[a-z2-7]{1,111}$")
HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class Form(str, Enum):
    """Which of the two descriptor shapes is in use."""

    MINIMAL = "MINIMAL"
    FULL = "FULL"


@dataclass(frozen=True)
class Descriptor:
    """A parsed asset descriptor."""

    form: Form
    collection: str
    index: int
    manifest_cid: str | None = None
    content_hash: str | None = None

    def to_string(self) -> str:
        """Rebuild the descriptor string this was parsed from."""
        parts = [TAG, self.collection, str(self.index)]
        if self.form is Form.FULL:
            parts += [self.manifest_cid or "", self.content_hash or ""]
        return SEPARATOR.join(parts)

    @property
    def asset_desc_hash(self) -> str:
        """The value recorded on chain for this descriptor."""
        return asset_desc_hash(self.to_string())


def asset_desc_hash(asset_desc: str) -> str:
    """Return ``assetDescHash`` for a descriptor string, as lowercase hex."""
    return hashlib.blake2b(
        asset_desc.encode("utf-8"), digest_size=32, person=ASSET_DESC_PERSONAL
    ).hexdigest()


def validate_slug(slug: str) -> str:
    """Return ``slug`` if it is a well-formed collection slug."""
    if not SLUG_PATTERN.match(slug):
        raise Invalid(
            f"collection slug {slug!r} must be 1-64 characters of [a-z0-9-] "
            "without leading, trailing or doubled hyphens"
        )
    return slug


def validate_index(index: int) -> int:
    """Return ``index`` if it is within the permitted range."""
    if not isinstance(index, int) or isinstance(index, bool):
        raise Invalid("item index must be an integer")
    if index < 0 or index > MAX_INDEX:
        raise Invalid(f"item index {index} is outside 0..{MAX_INDEX}")
    return index


def build(
    collection: str,
    index: int,
    manifest_cid: str | None = None,
    content_hash: str | None = None,
) -> Descriptor:
    """Construct a descriptor, minimal unless both full-form fields are given."""
    validate_slug(collection)
    validate_index(index)

    if manifest_cid is None and content_hash is None:
        return Descriptor(Form.MINIMAL, collection, index)
    if manifest_cid is None or content_hash is None:
        raise Invalid("full form requires both manifest_cid and content_hash")

    if not CID_PATTERN.match(manifest_cid):
        raise Invalid("manifest CID must be CIDv1, base32 lowercase, multibase prefix 'b'")
    if not HEX64_PATTERN.match(content_hash):
        raise Invalid("content hash must be 64 lowercase hexadecimal characters")

    descriptor = Descriptor(Form.FULL, collection, index, manifest_cid, content_hash)
    _check_length(descriptor.to_string())
    return descriptor


def parse(asset_desc: str) -> Descriptor:
    """Parse a descriptor string, or raise :class:`Invalid`."""
    if not isinstance(asset_desc, str):
        raise Invalid("asset_desc must be a string")
    _check_length(asset_desc)

    parts = asset_desc.split(SEPARATOR)
    if len(parts) == 3:
        form = Form.MINIMAL
    elif len(parts) == 5:
        form = Form.FULL
    else:
        raise Invalid(f"expected 3 or 5 fields separated by '|', got {len(parts)}")

    if parts[0] != TAG:
        raise Invalid(f"tag is {parts[0]!r}, not {TAG!r}")

    validate_slug(parts[1])

    if not INDEX_PATTERN.match(parts[2]):
        raise Invalid(f"index {parts[2]!r} must be decimal without leading zeros")
    index = validate_index(int(parts[2]))

    if form is Form.MINIMAL:
        return Descriptor(form, parts[1], index)

    if not CID_PATTERN.match(parts[3]):
        raise Invalid("manifest CID must be CIDv1, base32 lowercase, multibase prefix 'b'")
    if not HEX64_PATTERN.match(parts[4]):
        raise Invalid("content hash must be 64 lowercase hexadecimal characters")
    return Descriptor(form, parts[1], index, parts[3], parts[4])


def _check_length(asset_desc: str) -> None:
    size = len(asset_desc.encode("utf-8"))
    if size > MAX_ASSET_DESC_BYTES:
        raise Invalid(f"asset_desc is {size} bytes, over the {MAX_ASSET_DESC_BYTES} limit")
