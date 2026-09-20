"""Command line interface.

zmd1 hash zmd1:zecbit-genesis:1 ...
zmd1 parse <descriptor>
zmd1 canon <manifest.json>
zmd1 cid <manifest.json>
zmd1 verify <manifest.json> --descriptor ... --ik ... --network ...
zmd1 onchain --all --node <url> --txid <txid>
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import cid as cid_module
from .canonical import canonicalize
from .descriptor import Descriptor, asset_desc_hash, parse
from .errors import Invalid, NodeError, NodeUnreachable, Zmd1Error
from .manifest import content_hash, signing_digest, validate_schema
from .onchain import Node, find_in_transaction
from .verify import ChainContext, verify

DEFAULT_NODE = "https://dev.zebra.zsa-test.net"
GENESIS_TXID = "611ddfd4459e813b86b935fc05217f929e29c37cdc96ba8f23fc647e30c26317"
GENESIS_BATCH = 10

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_NOT_ON_CHAIN = 2
EXIT_UNREACHABLE = 3


def _load(path: str) -> Any:
    try:
        with Path(path).open(encoding="utf-8") as handle:
            return json.load(handle)
    except OSError as exc:
        raise Invalid(f"cannot read {path}: {exc}") from exc
    except ValueError as exc:
        raise Invalid(f"{path} is not valid JSON: {exc}") from exc


def _genesis_descriptors() -> list[Descriptor]:
    return [parse(f"zmd1|zecbit-genesis|{i}") for i in range(1, GENESIS_BATCH + 1)]


def _descriptors(values: Sequence[str], use_genesis: bool) -> list[Descriptor]:
    descriptors = [parse(value) for value in values]
    if use_genesis:
        descriptors += _genesis_descriptors()
    if not descriptors:
        raise Invalid("give one or more descriptors, or --all")
    return descriptors


def cmd_hash(args: argparse.Namespace) -> int:
    descriptors = _descriptors(args.descriptor, args.all)
    width = max(len(d.to_string()) for d in descriptors)
    for descriptor in descriptors:
        text = descriptor.to_string()
        print(f"{text:{width}s}  {descriptor.form.value:7s}  {asset_desc_hash(text)}")
    return EXIT_OK


def cmd_parse(args: argparse.Namespace) -> int:
    descriptor = parse(args.descriptor)
    print(
        json.dumps(
            {
                "form": descriptor.form.value,
                "collection": descriptor.collection,
                "index": descriptor.index,
                "manifest_cid": descriptor.manifest_cid,
                "content_hash": descriptor.content_hash,
                "asset_desc_hash": descriptor.asset_desc_hash,
            },
            indent=2,
        )
    )
    return EXIT_OK


def cmd_canon(args: argparse.Namespace) -> int:
    document = _load(args.manifest)
    sys.stdout.buffer.write(canonicalize(document))
    sys.stdout.buffer.write(b"\n")
    return EXIT_OK


def cmd_digest(args: argparse.Namespace) -> int:
    document = _load(args.manifest)
    print(f"content_hash   {content_hash(document)}")
    print(f"signing_digest {signing_digest(document)}")
    print(f"cid            {cid_module.encode(canonicalize(document))}")
    return EXIT_OK


def cmd_schema(args: argparse.Namespace) -> int:
    validate_schema(_load(args.manifest))
    print(f"{args.manifest}: matches the ZMD-1 item manifest schema")
    return EXIT_OK


def cmd_verify(args: argparse.Namespace) -> int:
    document = _load(args.manifest)
    descriptor = parse(args.descriptor)
    chain = ChainContext(
        asset_desc_hash=args.asset_desc_hash or descriptor.asset_desc_hash,
        ik=args.ik,
        network=args.network,
    )
    media = {int(i): Path(p).read_bytes() for i, p in (args.media or [])}
    result = verify(args.descriptor, document, chain, media=media, check_cid=args.check_cid)

    print(f"form              {result.form.value}")
    print(f"signature checked {result.signature_checked}")
    print(f"media checked     {result.media_checked}")
    print(f"cid checked       {result.cid_checked}")
    if not result.signature_checked:
        print("\nno signature verifier was supplied, so the creator's claim was not tested")
    return EXIT_OK


def cmd_onchain(args: argparse.Namespace) -> int:
    descriptors = _descriptors(args.descriptor, args.all)
    node = Node(args.node)

    width = max(len(d.to_string()) for d in descriptors)
    for descriptor in descriptors:
        text = descriptor.to_string()
        print(f"{text:{width}s}  {asset_desc_hash(text)}")

    print(f"\nchecking against {args.txid}")
    try:
        matches = find_in_transaction(node, args.txid, descriptors)
    except NodeError as exc:
        tip = node.chain_tip()
        print(f"\nnode reached, chain tip {tip}, but this transaction is not on it: {exc}")
        print("\nThe hashes above derive from the descriptor strings alone and do not")
        print("depend on any chain. Pass --txid for another issuance, or use `zmd1 hash`.")
        return EXIT_NOT_ON_CHAIN

    found = sum(1 for m in matches if m.present)
    print()
    for match in matches:
        state = "FOUND  " if match.present else "MISSING"
        print(f"{state} {match.asset_desc_hash}  {match.descriptor.to_string()}")
    print(f"\n{found}/{len(matches)} descriptors matched on-chain issuance data")
    return EXIT_OK if found == len(matches) else EXIT_INVALID


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zmd1", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_hash = sub.add_parser("hash", help="derive assetDescHash for descriptors")
    p_hash.add_argument("descriptor", nargs="*")
    p_hash.add_argument("--all", action="store_true", help="include the ZecBit Genesis batch")
    p_hash.set_defaults(func=cmd_hash)

    p_parse = sub.add_parser("parse", help="parse one descriptor")
    p_parse.add_argument("descriptor")
    p_parse.set_defaults(func=cmd_parse)

    p_canon = sub.add_parser("canon", help="print canonical manifest bytes")
    p_canon.add_argument("manifest")
    p_canon.set_defaults(func=cmd_canon)

    p_digest = sub.add_parser("digest", help="content hash, signing digest and CID")
    p_digest.add_argument("manifest")
    p_digest.set_defaults(func=cmd_digest)

    p_schema = sub.add_parser("schema", help="validate a manifest against the JSON Schema")
    p_schema.add_argument("manifest")
    p_schema.set_defaults(func=cmd_schema)

    p_verify = sub.add_parser("verify", help="run the full verification algorithm")
    p_verify.add_argument("manifest")
    p_verify.add_argument("--descriptor", required=True)
    p_verify.add_argument("--ik", required=True, help="issuance validating key, lowercase hex")
    p_verify.add_argument("--network", required=True, choices=["main", "test"])
    p_verify.add_argument(
        "--asset-desc-hash",
        dest="asset_desc_hash",
        help="value read from the chain; defaults to the descriptor's own hash",
    )
    p_verify.add_argument(
        "--media",
        nargs=2,
        action="append",
        metavar=("INDEX", "PATH"),
        help="media bytes to check against the manifest hash",
    )
    p_verify.add_argument("--check-cid", action="store_true")
    p_verify.set_defaults(func=cmd_verify)

    p_chain = sub.add_parser("onchain", help="check descriptors against a node")
    p_chain.add_argument("descriptor", nargs="*")
    p_chain.add_argument("--all", action="store_true", help="check the ZecBit Genesis batch")
    p_chain.add_argument("--node", default=DEFAULT_NODE)
    p_chain.add_argument("--txid", default=GENESIS_TXID)
    p_chain.set_defaults(func=cmd_onchain)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result: int = args.func(args)
        return result
    except NodeUnreachable as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_UNREACHABLE
    except Zmd1Error as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INVALID


if __name__ == "__main__":
    sys.exit(main())
