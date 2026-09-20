from __future__ import annotations

import pytest

import zmd1
from zmd1 import cid


def test_known_cid_for_hello_world():
    assert cid.encode(b"hello world") == (
        "bafkreifzjut3te2nhyekklss27nh3k72ysco7y32koao5eei66wof36n5e"
    )


def test_raw_sha256_cids_share_the_bafkrei_prefix():
    for payload in [b"", b"a", b"x" * 1000]:
        assert cid.encode(payload).startswith("bafkrei")


def test_decode_reports_the_parts():
    parsed = cid.decode(cid.encode(b"payload"))
    assert parsed.version == cid.CID_VERSION
    assert parsed.codec == cid.CODEC_RAW
    assert parsed.multihash_code == cid.MULTIHASH_SHA2_256
    assert len(parsed.digest) == 32


def test_matches_is_exact():
    encoded = cid.encode(b"payload")
    assert cid.matches(encoded, b"payload")
    assert not cid.matches(encoded, b"payloae")


def test_blake2b_multihash_round_trips():
    encoded = cid.encode(b"payload", cid.MULTIHASH_BLAKE2B_256)
    assert cid.decode(encoded).multihash_code == cid.MULTIHASH_BLAKE2B_256
    assert cid.matches(encoded, b"payload")
    assert encoded != cid.encode(b"payload")


def test_rejects_missing_multibase_prefix():
    with pytest.raises(zmd1.Invalid):
        cid.decode("afkreiabc")


def test_rejects_cidv0():
    with pytest.raises(zmd1.Invalid):
        cid.decode("bafybeiaaaa")  # v1 codec dag-pb is fine to parse
    with pytest.raises(zmd1.Invalid):
        cid.matches("b" + "a" * 8, b"payload")


def test_rejects_unknown_multihash():
    with pytest.raises(ValueError):
        cid.encode(b"payload", 0x99999)
