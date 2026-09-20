from __future__ import annotations

import pytest

import zmd1
from zmd1 import ChainContext, Form


@pytest.fixture()
def bundle(manifest_vector):
    return (
        manifest_vector["manifest"],
        manifest_vector["chain_context"]["ik"],
        manifest_vector["chain_context"]["network"],
        manifest_vector["media_bytes_utf8"].encode("utf-8"),
        manifest_vector["descriptors"],
    )


def context(descriptor, ik, network):
    return ChainContext(descriptor["asset_desc_hash"], ik, network)


def test_minimal_form(bundle):
    manifest, ik, network, _, descriptors = bundle
    d = descriptors["minimal"]
    result = zmd1.verify(d["asset_desc"], manifest, context(d, ik, network))
    assert result.form is Form.MINIMAL
    assert result.signature_checked is False
    assert result.media_checked == 0


def test_full_form_with_cid(bundle):
    manifest, ik, network, media, descriptors = bundle
    d = descriptors["full"]
    result = zmd1.verify(
        d["asset_desc"], manifest, context(d, ik, network), media={0: media}, check_cid=True
    )
    assert result.form is Form.FULL
    assert result.cid_checked is True
    assert result.media_checked == 1


def test_rejects_chain_hash_mismatch(bundle):
    manifest, ik, network, _, descriptors = bundle
    d = descriptors["minimal"]
    with pytest.raises(zmd1.Invalid, match="chain records"):
        zmd1.verify(d["asset_desc"], manifest, ChainContext("0" * 64, ik, network))


def test_rejects_tampered_manifest_in_full_form(bundle):
    manifest, ik, network, _, descriptors = bundle
    d = descriptors["full"]
    altered = dict(manifest)
    altered["item"] = dict(manifest["item"], name="renamed after commitment")
    with pytest.raises(zmd1.Invalid, match="descriptor commits to"):
        zmd1.verify(d["asset_desc"], altered, context(d, ik, network))


def test_minimal_form_tolerates_manifest_edits(bundle):
    manifest, ik, network, _, descriptors = bundle
    d = descriptors["minimal"]
    altered = dict(manifest)
    altered["item"] = dict(manifest["item"], name="renamed")
    assert zmd1.verify(d["asset_desc"], altered, context(d, ik, network)).form is Form.MINIMAL


def test_rejects_slug_mismatch(bundle):
    manifest, ik, network, _, _ = bundle
    desc = "zmd1|other-collection|1"
    with pytest.raises(zmd1.Invalid, match="slug"):
        zmd1.verify(desc, manifest, ChainContext(zmd1.asset_desc_hash(desc), ik, network))


def test_rejects_index_mismatch(bundle):
    manifest, ik, network, _, _ = bundle
    desc = "zmd1|zecbit-genesis|2"
    with pytest.raises(zmd1.Invalid, match="index"):
        zmd1.verify(desc, manifest, ChainContext(zmd1.asset_desc_hash(desc), ik, network))


def test_rejects_foreign_issuer(bundle):
    manifest, _, network, _, descriptors = bundle
    d = descriptors["minimal"]
    chain = ChainContext(d["asset_desc_hash"], "b" * 64, network)
    with pytest.raises(zmd1.Invalid, match="issuer_vk"):
        zmd1.verify(d["asset_desc"], manifest, chain)


def test_rejects_network_replay(bundle):
    manifest, ik, _, _, descriptors = bundle
    d = descriptors["minimal"]
    chain = ChainContext(d["asset_desc_hash"], ik, "main")
    with pytest.raises(zmd1.Invalid, match="network"):
        zmd1.verify(d["asset_desc"], manifest, chain)


def test_rejects_wrong_schema_version(bundle):
    manifest, ik, network, _, descriptors = bundle
    d = descriptors["minimal"]
    altered = dict(manifest, schema_version="zmd2")
    with pytest.raises(zmd1.Invalid, match="schema_version"):
        zmd1.verify(d["asset_desc"], altered, context(d, ik, network))


def test_rejects_substituted_media(bundle):
    manifest, ik, network, _, descriptors = bundle
    d = descriptors["minimal"]
    with pytest.raises(zmd1.Invalid, match=r"media\[0\]"):
        zmd1.verify(d["asset_desc"], manifest, context(d, ik, network), media={0: b"other"})


def test_rejects_media_index_outside_the_manifest(bundle):
    manifest, ik, network, media, descriptors = bundle
    d = descriptors["minimal"]
    with pytest.raises(zmd1.Invalid, match="no such entry"):
        zmd1.verify(d["asset_desc"], manifest, context(d, ik, network), media={5: media})


def test_unfetched_media_is_not_checked(bundle):
    manifest, ik, network, _, descriptors = bundle
    d = descriptors["minimal"]
    result = zmd1.verify(d["asset_desc"], manifest, context(d, ik, network), media={})
    assert result.media_checked == 0


def test_signature_verifier_receives_the_digest(bundle):
    manifest, ik, network, _, descriptors = bundle
    d = descriptors["minimal"]
    seen = {}

    def verifier(key, digest, signature):
        seen.update(key=key, digest=digest, signature=signature)
        return True

    result = zmd1.verify(
        d["asset_desc"], manifest, context(d, ik, network), verify_signature=verifier
    )
    assert result.signature_checked is True
    assert seen["key"] == ik
    assert seen["digest"] == zmd1.signing_digest(manifest)
    assert seen["signature"] == manifest["creator"]["sig"]


def test_rejects_failed_signature(bundle):
    manifest, ik, network, _, descriptors = bundle
    d = descriptors["minimal"]
    with pytest.raises(zmd1.Invalid, match="signature does not verify"):
        zmd1.verify(
            d["asset_desc"],
            manifest,
            context(d, ik, network),
            verify_signature=lambda *args: False,
        )


def test_rejects_absent_signature_when_checking(bundle):
    manifest, ik, network, _, descriptors = bundle
    d = descriptors["minimal"]
    altered = dict(manifest, creator={"name": "ZecBit"})
    with pytest.raises(zmd1.Invalid, match="no creator signature"):
        zmd1.verify(
            d["asset_desc"],
            altered,
            context(d, ik, network),
            verify_signature=lambda *args: True,
        )
