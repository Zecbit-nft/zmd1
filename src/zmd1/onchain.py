"""Reading asset identities from a Zcash node.

Only the JSON-RPC calls needed to answer one question: does this
``assetDescHash`` appear in that issuance transaction.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Sequence
from typing import Any, NamedTuple

from .descriptor import Descriptor, asset_desc_hash
from .errors import NodeError, NodeUnreachable

DEFAULT_TIMEOUT = 30


class Node:
    """A JSON-RPC client for a Zcash node."""

    def __init__(self, url: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.url = url
        self.timeout = timeout

    def call(self, method: str, params: Sequence[Any] | None = None) -> Any:
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": list(params or [])}
        ).encode("utf-8")
        request = urllib.request.Request(
            self.url, data=payload, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.load(response)
        except urllib.error.URLError as exc:
            raise NodeUnreachable(f"cannot reach {self.url}: {exc.reason}") from exc
        except (ValueError, OSError) as exc:
            raise NodeUnreachable(f"cannot read a response from {self.url}: {exc}") from exc

        error = body.get("error")
        if error:
            code = error.get("code") if isinstance(error, dict) else None
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise NodeError(str(message), code)
        if "result" not in body:
            raise NodeError(f"response from {self.url} carried neither result nor error")
        return body["result"]

    def chain_tip(self) -> int | None:
        """Return the node's block height, or ``None`` if it will not say."""
        try:
            info = self.call("getblockchaininfo")
        except (NodeError, NodeUnreachable):
            return None
        return info.get("blocks") if isinstance(info, dict) else None

    def raw_transaction(self, txid: str) -> dict[str, Any]:
        """Return a verbose ``getrawtransaction`` result."""
        result: dict[str, Any] = self.call("getrawtransaction", [txid, 1])
        return result


class Match(NamedTuple):
    """Whether one descriptor's hash was found in a transaction."""

    descriptor: Descriptor
    asset_desc_hash: str
    present: bool


def find_in_transaction(node: Node, txid: str, descriptors: Sequence[Descriptor]) -> list[Match]:
    """Report which descriptors' hashes appear in an issuance transaction.

    The issuance bundle stores each ``assetDescHash`` verbatim, so a hash that
    belongs to the transaction appears in its serialization. This is a
    substring search over the raw hex rather than a parse of the bundle: it
    shows a hash is present, not which issuance action carries it.
    """
    raw = str(node.raw_transaction(txid).get("hex", "")).lower()
    matches = []
    for descriptor in descriptors:
        digest = asset_desc_hash(descriptor.to_string())
        matches.append(Match(descriptor, digest, digest in raw))
    return matches
