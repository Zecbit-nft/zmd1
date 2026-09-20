from __future__ import annotations

import hashlib

import pytest

import zmd1


def test_vector_hashes(manifest_vector):
    manifest = manifest_vector["manifest"]
    assert zmd1.canonicalize(manifest).decode("utf-8") == manifest_vector["canonical_utf8"]
    assert zmd1.content_hash(manifest) == manifest_vector["content_hash"]
    assert zmd1.signing_digest(manifest) == manifest_vector["signing_digest"]
    assert zmd1.encode_cid(zmd1.canonicalize(manifest)) == manifest_vector["manifest_cid"]


def test_vector_media_hash(manifest_vector):
    media = manifest_vector["media_bytes_utf8"].encode("utf-8")
    assert zmd1.media_hash(media) == manifest_vector["media_hash"]
    assert zmd1.media_hash(media) == manifest_vector["manifest"]["media"][0]["hash"]


def test_signing_digest_excludes_the_signature(manifest_vector):
    manifest = manifest_vector["manifest"]
    altered = dict(manifest)
    altered["creator"] = dict(manifest["creator"], sig="ff" * 64)
    assert zmd1.signing_digest(altered) == zmd1.signing_digest(manifest)


def test_signing_digest_covers_everything_else(manifest_vector):
    manifest = manifest_vector["manifest"]
    altered = dict(manifest)
    altered["item"] = dict(manifest["item"], name="renamed")
    assert zmd1.signing_digest(altered) != zmd1.signing_digest(manifest)


def test_signing_digest_is_domain_separated(manifest_vector):
    manifest = manifest_vector["manifest"]
    unsigned = dict(manifest)
    unsigned["creator"] = {k: v for k, v in manifest["creator"].items() if k != "sig"}
    undomained = hashlib.blake2b(zmd1.canonicalize(unsigned), digest_size=32).hexdigest()
    assert zmd1.signing_digest(manifest) != undomained


def test_signing_digest_requires_a_creator():
    with pytest.raises(zmd1.Invalid):
        zmd1.signing_digest({"schema_version": "zmd1"})


def test_schema_is_loadable():
    loaded = zmd1.schema()
    assert loaded["title"] == "ZMD-1 Item Manifest"
    assert loaded["required"] == ["schema_version", "collection", "item", "media", "creator"]


def test_schema_accepts_the_vector(manifest_vector):
    pytest.importorskip("jsonschema")
    zmd1.validate_schema(manifest_vector["manifest"])


def test_schema_rejects_a_missing_required_field(manifest_vector):
    pytest.importorskip("jsonschema")
    broken = {k: v for k, v in manifest_vector["manifest"].items() if k != "media"}
    with pytest.raises(zmd1.Invalid):
        zmd1.validate_schema(broken)
