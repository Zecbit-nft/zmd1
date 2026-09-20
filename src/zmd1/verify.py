"""The ZMD-1 verification algorithm.

Six steps, in an order chosen so the cheapest check that can reject runs first.
Any failure raises :class:`~zmd1.errors.Invalid` and the whole bundle is
discarded; there is no partial trust.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable, NamedTuple

from . import cid as cid_module
from .descriptor import Descriptor, Form, asset_desc_hash, parse
from .errors import Invalid
from .manifest import SCHEMA_VERSION, content_hash, media_hash, signing_digest

SignatureVerifier = Callable[[str, str, str], bool]


class ChainContext(NamedTuple):
    """What a verifier read from the chain for this asset.

    ``asset_desc_hash`` is the value in the issuance bundle, ``ik`` is the
    issuance validating key as lowercase hex, and ``network`` is ``"main"`` or
    ``"test"``.
    """

    asset_desc_hash: str
    ik: str
    network: str


class Result(NamedTuple):
    """What a successful verification established.

    ``FULL`` means the chain commits to every byte of the manifest and, through
    the media hashes, to every byte of the media that was checked. ``MINIMAL``
    means the chain commits to ``(collection, index)`` and the creator's
    signature is what stands behind the manifest.

    ``signature_checked`` is ``False`` when no verifier was supplied. In the
    minimal form that leaves nothing backing the manifest, so callers must not
    present an unchecked minimal bundle as verified.
    """

    descriptor: Descriptor
    signature_checked: bool
    media_checked: int
    cid_checked: bool

    @property
    def form(self) -> Form:
        return self.descriptor.form


def verify(
    asset_desc: str,
    manifest: Mapping[str, Any],
    chain: ChainContext,
    media: Mapping[int, bytes] | None = None,
    verify_signature: SignatureVerifier | None = None,
    check_cid: bool = False,
) -> Result:
    """Verify a manifest against a descriptor and the chain."""
    computed = asset_desc_hash(asset_desc)
    expected = chain.asset_desc_hash.lower()
    if computed != expected:
        raise Invalid(f"asset_desc hashes to {computed}, chain records {expected}")

    descriptor = parse(asset_desc)

    cid_checked = False
    if descriptor.form is Form.FULL:
        from .canonical import canonicalize

        canonical_bytes = canonicalize(manifest)
        digest = content_hash(manifest)
        if digest != descriptor.content_hash:
            raise Invalid(
                f"manifest hashes to {digest}, descriptor commits to {descriptor.content_hash}"
            )
        if check_cid:
            if not cid_module.matches(descriptor.manifest_cid or "", canonical_bytes):
                raise Invalid("manifest CID does not address the canonical manifest bytes")
            cid_checked = True

    _check_cross_fields(descriptor, manifest, chain)

    signature_checked = False
    if verify_signature is not None:
        creator = manifest.get("creator")
        signature = creator.get("sig") if isinstance(creator, Mapping) else None
        if not signature:
            raise Invalid("manifest carries no creator signature")
        if not verify_signature(chain.ik, signing_digest(manifest), signature):
            raise Invalid("creator signature does not verify under the issuance key")
        signature_checked = True

    media_checked = _check_media(manifest, media)

    return Result(descriptor, signature_checked, media_checked, cid_checked)


def _check_cross_fields(
    descriptor: Descriptor, manifest: Mapping[str, Any], chain: ChainContext
) -> None:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise Invalid(
            f"schema_version is {manifest.get('schema_version')!r}, not {SCHEMA_VERSION!r}"
        )

    collection = manifest.get("collection")
    item = manifest.get("item")
    if not isinstance(collection, Mapping) or not isinstance(item, Mapping):
        raise Invalid("manifest must carry collection and item objects")

    if collection.get("slug") != descriptor.collection:
        raise Invalid(
            f"manifest slug {collection.get('slug')!r} does not match "
            f"descriptor {descriptor.collection!r}"
        )
    if item.get("index") != descriptor.index:
        raise Invalid(
            f"manifest index {item.get('index')!r} does not match descriptor {descriptor.index}"
        )

    issuer = collection.get("issuer_vk")
    if not isinstance(issuer, str) or issuer.lower() != chain.ik.lower():
        raise Invalid("manifest issuer_vk is not the key that issued this asset")

    if collection.get("network") != chain.network:
        raise Invalid(
            f"manifest network {collection.get('network')!r} does not match chain {chain.network!r}"
        )


def _check_media(manifest: Mapping[str, Any], media: Mapping[int, bytes] | None) -> int:
    if not media:
        return 0

    entries = manifest.get("media")
    if not isinstance(entries, list):
        raise Invalid("manifest media must be an array")

    checked = 0
    for index, data in media.items():
        if index < 0 or index >= len(entries):
            raise Invalid(f"media[{index}] was supplied but the manifest has no such entry")
        declared = entries[index].get("hash") if isinstance(entries[index], Mapping) else None
        if not isinstance(declared, str):
            raise Invalid(f"media[{index}] in the manifest has no hash")
        digest = media_hash(data)
        if digest != declared.lower():
            raise Invalid(f"media[{index}] hashes to {digest}, manifest declares {declared}")
        checked += 1
    return checked
