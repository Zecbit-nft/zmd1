# zmd1

[![CI](https://github.com/Zecbit-nft/zmd1/actions/workflows/ci.yml/badge.svg)](https://github.com/Zecbit-nft/zmd1/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Reference implementation of **ZMD-1**, a metadata standard for NFTs issued as
Zcash Shielded Assets.

No dependencies outside the Python standard library. The specification is
[SPEC.md](SPEC.md); conformance vectors for other implementations are in
[`vectors/`](vectors/).

Not on PyPI yet. Install from source:

```bash
pip install git+https://github.com/Zecbit-nft/zmd1
```

```bash
zmd1 hash 'zmd1|zecbit-genesis|1'
# zmd1|zecbit-genesis|1  MINIMAL  2564d2f0815a25524bdd956509f232445eaf5dce202988d683cd616b722487af
```

## Status of the asset layer it builds on

ZMD-1 describes metadata for custom assets under ZIP 226 and ZIP 227. **Those
are drafts, and at the time of writing they are not scheduled for any Zcash
network upgrade.** The transaction format they depend on was withdrawn, its
successor states it need not carry custom assets, and the fee specification's
asset clauses were removed.

That does not make the design wrong, and the identity derivation here is
testable today with no chain at all. It does mean anything built on ZMD-1 has a
timeline nobody controls.

For items that work on the Orchard pool as deployed, see
[nscv](https://github.com/Zecbit-nft/nscv), published by the same organisation.
It makes a different trade: it works now, and ownership is never public.

The canonicalization advice differs between the two repositories, which looks
like a contradiction and is not. ZMD-1 binds a **JSON document**, and JSON has
many byte encodings of the same value, so it must fix one: RFC 8785. nscv binds
**fixed-layout binary**, which has exactly one encoding already, so it hashes
bytes as published and does not canonicalize at all.

## How an NFT gets its identity on Zcash

Under ZIP 227 an asset's identity is a pair: the issuance key, and a 32-byte
hash of a byte string the issuer chooses.

```
AssetId       = (ik, assetDescHash)
assetDescHash = BLAKE2b-256(asset_desc, person="ZSA-AssetDescCRH")
```

**Only the hash goes on chain.** ZIP 227 puts it there rather than the string
because a consensus-replicated store of arbitrary issuer-supplied bytes bloats
every full node forever and puts unvetted content in front of node operators. A
hash commitment binds the same thing at fixed cost.

Two properties fall out of that, and they are why this works on a privacy chain:

- Anyone holding the string can prove the binding by re-hashing it. No registry,
  no API, no permission.
- Nobody can recover the string from the chain. Metadata stays private until its
  holder chooses to disclose it.

Identity is welded to the issuer too. Two issuers publishing byte-identical
descriptions produce different asset identities, because the key is half the
pair. Impersonating a collection means forging a signature, not copying a name.

ZIP 227 stops there and says the byte string is opaque. **ZMD-1 defines what
goes in it.**

## The descriptor

```abnf
asset-desc   = minimal-form / full-form
minimal-form = "zmd1" "|" collection "|" index
full-form    = "zmd1" "|" collection "|" index "|" manifest-cid "|" content-hash
```

The grammar is deliberately narrow: lowercase only, no whitespace, no non-ASCII,
no leading zeros on the index. Those are not style rules. The string is hashed
into an identity, so two spellings that look alike and hash differently are a
homoglyph attack waiting to happen.

| | minimal | full |
|---|---|---|
| Chain commits to | collection, index | collection, index, every byte of the manifest, every byte of the media |
| Metadata revisable after issuance | yes, re-signed | no — one byte is a different asset |
| What backs the manifest | the creator's signature | the chain |

`verify()` reports which one it established. Callers must not blur them.

## Usage

```python
import zmd1

descriptor = zmd1.parse("zmd1|zecbit-genesis|1")
descriptor.collection  # 'zecbit-genesis'
descriptor.index  # 1
descriptor.form  # <Form.MINIMAL>
descriptor.asset_desc_hash  # '2564d2f0…87af'
```

Building a full-form descriptor from a manifest:

```python
canonical = zmd1.canonicalize(manifest)

descriptor = zmd1.build(
    "zecbit-genesis",
    1,
    manifest_cid=zmd1.encode_cid(canonical),
    content_hash=zmd1.content_hash(manifest),
)
```

Verifying a bundle against what you read from the chain:

```python
result = zmd1.verify(
    descriptor.to_string(),
    manifest,
    zmd1.ChainContext(asset_desc_hash=on_chain_hash, ik=issuer_key, network="test"),
    media={0: image_bytes},
    check_cid=True,
)

result.form  # <Form.FULL>
result.media_checked  # 1
result.signature_checked  # False — see below
```

Any failure raises `zmd1.Invalid`. There is no partial trust: a bundle whose
media hash is wrong does not get to display its name.

### Signatures are pluggable, on purpose

`verify_signature` is a callable you supply, `(ik, digest, sig) -> bool`.

ZMD-1's contribution is the digest:
`BLAKE2b-256("ZMD1-ItemSig" || JCS(M without creator.sig))`. BIP-340
verification is a commodity, and a hand-rolled one is a worse outcome than an
honest "unchecked". When no verifier is passed, `result.signature_checked` is
`False` — and in the minimal form the signature is the *only* thing backing the
manifest, so ignoring that flag means trusting an unsigned document.

### Canonicalization

Two parties must serialize the same manifest to the same bytes or the hash means
nothing. ZMD-1 uses JCS (RFC 8785) with one addition: every number must be an
integer inside 53 bits, which removes the floating-point problem instead of
solving it. Fractional trait values go in as strings.

`sort_keys=True` will not do. U+10000 encodes to the surrogate pair
`D800 DC00`, and `D800` is below `FF3A`, so by UTF-16 code unit U+10000 sorts
before `Ｚ` while by code point it sorts after. Sorting by code point produces a
different content hash for the same manifest. There is a test for exactly this.

## Command line

```bash
zmd1 hash 'zmd1|zecbit-genesis|1' 'zmd1|zecbit-genesis|2'
zmd1 parse 'zmd1|zecbit-genesis|1'
zmd1 canon manifest.json
zmd1 digest manifest.json
zmd1 schema manifest.json          # needs zmd1[schema]
zmd1 verify manifest.json --descriptor 'zmd1|g|1' --ik <hex> --network test
zmd1 onchain --all --node <url> --txid <txid>
```

Exit codes: `0` success, `1` invalid, `2` transaction not on the chain,
`3` node unreachable.

`zmd1 onchain` does a substring match over the raw transaction hex. That shows a
hash is present in the transaction; it does not parse the issuance bundle and
does not tell you which action carries it. Said plainly because the distinction
matters if you are relying on the result.

### Note on the ZSA test network

The default `--txid` points at ZecBit's 10-asset batch issuance on the public
ZSA test network. **That transaction is not on the current chain: the network
was reset, and block 251 now holds unrelated transactions.**

The hashes are unaffected, being a function of the descriptor strings and
nothing else. `zmd1 onchain` reports the two cases separately and exits 2 rather
than printing a row of MISSING that reads like a broken setup.

## Conformance vectors

[`vectors/`](vectors/) holds machine-readable test vectors for independent
implementations: the descriptor grammar with 6 accepted and 16 rejected cases,
canonicalization output with digests and CIDs, and one worked item end to end.

This repository's own test suite consumes them, so they cannot drift from the
implementation without turning CI red.

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check . && ruff format --check .
mypy
```

58 tests. Most are rejection cases, because the useful property of a verifier is
not that it accepts good bundles.

## License

MIT.
