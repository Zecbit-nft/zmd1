from __future__ import annotations

import pytest

import zmd1
from zmd1.descriptor import MAX_INDEX, Form


def test_vectors_accept(descriptor_vectors):
    for case in descriptor_vectors["valid"]:
        parsed = zmd1.parse(case["asset_desc"])
        assert parsed.form.value == case["form"]
        assert parsed.collection == case["collection"]
        assert parsed.index == case["index"]
        assert parsed.asset_desc_hash == case["asset_desc_hash"]


def test_vectors_reject(descriptor_vectors):
    for case in descriptor_vectors["invalid"]:
        with pytest.raises(zmd1.Invalid):
            zmd1.parse(case["asset_desc"])


def test_round_trip(descriptor_vectors):
    for case in descriptor_vectors["valid"]:
        assert zmd1.parse(case["asset_desc"]).to_string() == case["asset_desc"]


def test_published_genesis_identities():
    assert zmd1.asset_desc_hash("zmd1|zecbit-genesis|1") == (
        "2564d2f0815a25524bdd956509f232445eaf5dce202988d683cd616b722487af"
    )
    assert zmd1.asset_desc_hash("zmd1|zecbit-genesis|10") == (
        "e83bc891da073ff09d5f4caf303f16842500de7a0866c64cea74a85de220f2e0"
    )


def test_personalization_changes_the_hash():
    import hashlib

    plain = hashlib.blake2b(b"zmd1|zecbit-genesis|1", digest_size=32).hexdigest()
    assert zmd1.asset_desc_hash("zmd1|zecbit-genesis|1") != plain


def test_one_byte_changes_the_identity():
    assert zmd1.asset_desc_hash("zmd1|g|1") != zmd1.asset_desc_hash("zmd1|g|2")


def test_build_minimal():
    descriptor = zmd1.build("zecbit-genesis", 1)
    assert descriptor.form is Form.MINIMAL
    assert descriptor.to_string() == "zmd1|zecbit-genesis|1"


def test_build_full():
    descriptor = zmd1.build("g", 0, zmd1.encode_cid(b"bytes"), "a" * 64)
    assert descriptor.form is Form.FULL
    assert zmd1.parse(descriptor.to_string()) == descriptor


def test_build_rejects_half_a_full_form():
    with pytest.raises(zmd1.Invalid):
        zmd1.build("g", 0, zmd1.encode_cid(b"bytes"), None)
    with pytest.raises(zmd1.Invalid):
        zmd1.build("g", 0, None, "a" * 64)


def test_build_rejects_out_of_range_index():
    with pytest.raises(zmd1.Invalid):
        zmd1.build("g", MAX_INDEX + 1)
    with pytest.raises(zmd1.Invalid):
        zmd1.build("g", -1)


def test_build_rejects_boolean_index():
    with pytest.raises(zmd1.Invalid):
        zmd1.build("g", True)


def test_non_string_descriptor():
    with pytest.raises(zmd1.Invalid):
        zmd1.parse(None)
