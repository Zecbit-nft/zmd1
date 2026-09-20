from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

VECTORS = Path(__file__).resolve().parent.parent / "vectors"


def _load(name: str) -> Any:
    with (VECTORS / name).open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="session")
def descriptor_vectors() -> Any:
    return _load("descriptors.json")


@pytest.fixture(scope="session")
def canonicalization_vectors() -> Any:
    return _load("canonicalization.json")


@pytest.fixture(scope="session")
def manifest_vector() -> Any:
    return _load("manifest.json")
