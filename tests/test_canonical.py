from __future__ import annotations

import hashlib

import pytest

import zmd1
from zmd1 import cid
from zmd1.canonical import MAX_SAFE_INTEGER, loads


def test_vectors(canonicalization_vectors):
    for case in canonicalization_vectors:
        produced = zmd1.canonicalize(case["document"])
        assert produced.decode("utf-8") == case["canonical"], case["label"]
        assert hashlib.blake2b(produced, digest_size=32).hexdigest() == case["blake2b_256"]
        assert cid.encode(produced) == case["cid"]


def test_key_order_is_independent_of_insertion_order():
    assert zmd1.canonicalize({"b": 1, "a": 2}) == zmd1.canonicalize({"a": 2, "b": 1})


def test_sorted_by_utf16_code_unit_not_code_point():
    high = "\U00010000"
    wide = "\uff3a"
    assert high.encode("utf-16-be") < wide.encode("utf-16-be")
    assert high > wide
    out = zmd1.canonicalize({wide: 2, high: 1}).decode("utf-8")
    assert out.index(high) < out.index(wide)


def test_no_insignificant_whitespace():
    assert zmd1.canonicalize({"a": [1, 2]}) == b'{"a":[1,2]}'


def test_non_ascii_is_not_escaped():
    assert zmd1.canonicalize({"a": "\u00e9"}) == '{"a":"\u00e9"}'.encode()


def test_control_characters_are_escaped():
    assert zmd1.canonicalize({"a": "\n"}) == b'{"a":"\\n"}'
    assert zmd1.canonicalize({"a": "\t"}) == b'{"a":"\\t"}'
    assert zmd1.canonicalize({"a": "\x00"}) == b'{"a":"\\u0000"}'
    assert zmd1.canonicalize({"a": '"\\'}) == b'{"a":"\\"\\\\"}'


def test_rejects_floats():
    with pytest.raises(zmd1.Invalid):
        zmd1.canonicalize({"a": 1.5})


def test_accepts_max_safe_integer():
    assert zmd1.canonicalize({"a": MAX_SAFE_INTEGER}) == f'{{"a":{MAX_SAFE_INTEGER}}}'.encode()


def test_rejects_oversize_integers():
    with pytest.raises(zmd1.Invalid):
        zmd1.canonicalize({"a": MAX_SAFE_INTEGER + 1})
    with pytest.raises(zmd1.Invalid):
        zmd1.canonicalize({"a": -(MAX_SAFE_INTEGER + 1)})


def test_booleans_and_null():
    assert zmd1.canonicalize({"a": True, "b": False, "c": None}) == b'{"a":true,"b":false,"c":null}'


def test_error_path_points_at_the_offender():
    with pytest.raises(zmd1.Invalid, match=r"\$\.a\[1\]\.b"):
        zmd1.canonicalize({"a": [0, {"b": 1.5}]})


def test_loads_rejects_uncanonicalizable_json():
    with pytest.raises(zmd1.Invalid):
        loads(b'{"a": 1.5}')


def test_loads_rejects_malformed_json():
    with pytest.raises(zmd1.Invalid):
        loads(b"{not json")
