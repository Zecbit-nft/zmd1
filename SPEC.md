# ZMD-1 — Metadata for Zcash Shielded Assets

Version 1.0. The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are to be
interpreted as described in RFC 2119.

## 1. Scope

ZIP 227 gives an asset an identity derived from an issuance key and an
issuer-chosen byte string. It does not say what that byte string contains.
ZMD-1 defines a structure for it, a metadata document to go with it, and the
algorithm a verifier runs to decide whether the two belong together.

ZMD-1 is off-chain. Nothing in it changes consensus, and a node that has never
heard of it validates ZMD-1 assets exactly as it validates any other.

## 2. Identity

Under ZIP 227 an asset's identity is the pair:

```
AssetId       = (ik, assetDescHash)
assetDescHash = BLAKE2b-256(asset_desc, person = "ZSA-AssetDescCRH")
```

`ik` is the issuance validating key. `asset_desc` is the issuer's byte string.
Only `assetDescHash` is recorded on chain.

Two consequences are load-bearing for everything below.

Anyone holding `asset_desc` can prove the binding by re-hashing it. No registry,
no API and no permission is involved.

Nobody can recover `asset_desc` from the chain. Metadata is private until its
holder discloses it.

Identity is also welded to the issuer: two issuers publishing byte-identical
descriptions produce different AssetIds. Impersonating a collection requires
forging a signature under `ik`, not copying a name.

## 3. The descriptor

### 3.1 Grammar

```abnf
asset-desc     = minimal-form / full-form

minimal-form   = tag SEP collection SEP index
full-form      = tag SEP collection SEP index SEP manifest-cid SEP content-hash

tag            = %s"zmd1"
SEP            = %x7C                    ; "|"

collection     = slug
slug           = slug-edge [ *62slug-char slug-edge ]
slug-edge      = %x61-7A / DIGIT
slug-char      = slug-edge / "-"

index          = "0" / ( nz-digit *9DIGIT )
nz-digit       = %x31-39

manifest-cid   = "b" 1*111cid-char
cid-char       = %x61-7A / %x32-37

content-hash   = 64hex-lower
hex-lower      = DIGIT / %x61-66
```

A descriptor MUST NOT exceed 256 bytes when encoded as UTF-8.

### 3.2 Field rules

**`tag`** is the literal `zmd1`. Parsers MUST match case-sensitively. A string
carrying any other tag MUST NOT be interpreted under this specification.

**`collection`** is 1 to 64 characters from `[a-z0-9-]`. It MUST NOT begin or
end with a hyphen and MUST NOT contain two consecutive hyphens.

The slug is a machine identifier, not a display name. Uppercase, whitespace and
non-ASCII characters are excluded because the string is hashed into an identity:
any two spellings that look alike and hash differently are a homoglyph attack.
The human-readable name lives in the manifest.

**`index`** is the item's ordinal within the collection, decimal, without
leading zeros, in the range 0 to 4294967295.

Issuers SHOULD assign indices sequentially and MUST NOT reuse an index within a
collection. The protocol does not enforce this: two descriptors sharing
`(collection, index)` but differing in their trailing fields are distinct
assets. Clients MUST therefore treat a collision on `(ik, collection, index)`
across distinct asset identities as an anomaly worth flagging.

**`manifest-cid`** (full form only) is the CIDv1 of the canonical manifest
bytes, base32 lowercase, multibase prefix `b`. Issuers MUST use CIDv1; CIDv0 is
not permitted, because its mixed-case alphabet conflicts with the lowercase byte
discipline of this grammar. The CID SHOULD use the `raw` multicodec so the
addressed block is exactly the canonical manifest byte string.

**`content-hash`** (full form only) is BLAKE2b-256 of the canonical manifest
bytes, 64 lowercase hexadecimal characters.

`content-hash`, not the CID, is the normative binding. Verifiers MUST check
`content-hash` and MAY check the CID. The CID exists for retrieval; the hash
exists for truth.

### 3.3 The two forms

| | minimal | full |
|---|---|---|
| Chain commits to | collection and index | collection, index, every byte of the manifest, and transitively every byte of the media |
| Metadata may change after issuance | yes, re-signed by the creator | no; one changed byte is a different asset |
| What backs the manifest | the creator's signature | the chain |

Both are conformant. An issuer chooses immutability or revisability, and a
verifier MUST report which one it established.

## 4. The manifest

A JSON document. The normative schema is `src/zmd1/schema/item-manifest.json`.

Required members are `schema_version`, `collection`, `item`, `media` and
`creator`. `schema_version` MUST be the string `zmd1`.

`collection.issuer_vk` MUST equal the issuance validating key in the on-chain
issuance bundle. `collection.network` MUST be `main` or `test` and guards
against a manifest minted for one network being replayed against an identically
constructed asset on the other.

`media[].hash` is BLAKE2b-256 of the exact media bytes and binds them regardless
of transport. `media[].cid` is a retrieval hint. Verifiers MUST check `hash` and
MAY check `cid`.

`created_at` is informational and unverifiable. Clients MUST NOT present it as a
proven timestamp; the proven timestamp of an item is its issuance block.

Objects permit additional properties. Unknown members MUST be preserved
byte-for-byte when hashing and MUST NOT be silently dropped.

### 4.1 Canonicalization

The manifest's byte serialization is fixed so that independent implementations
reproduce the same `content-hash`. ZMD-1 adopts JCS (RFC 8785):

1. Object keys are sorted by UTF-16 code unit.
2. No insignificant whitespace.
3. Strings use the minimal escaping JCS prescribes, UTF-8 encoded.
4. Every number MUST be an integer representable in 53 bits. Fractional values
   MUST be expressed as strings.

Rule 4 is ZMD-1's, not RFC 8785's. It removes floating-point serialization
ambiguity rather than solving it.

Rule 1 is not satisfied by sorting on Unicode code point. U+10000 encodes to the
surrogate pair `D800 DC00`, and `D800` is below `FF3A`, so by UTF-16 code unit
U+10000 precedes U+FF3A while by code point it follows. An implementation that
sorts by code point produces a different content hash for the same manifest.

### 4.2 Creator signature

```
signing_digest = BLAKE2b-256( "ZMD1-ItemSig" || JCS(M without creator.sig) )
```

The signature is made with the issuance key, so manifest authorship is provable
by exactly the party the chain already recognises as the issuer. It covers the
manifest with its own signature removed, because a signature cannot cover
itself, and is domain-separated so it cannot be replayed as another digest.

## 5. Verification

Given `asset_desc`, a manifest `M`, and chain context
`(assetDescHash, ik, network)`, a verifier MUST perform the following in order.

1. **Chain binding.** `BLAKE2b-256(asset_desc, person="ZSA-AssetDescCRH")`
   equals the chain's `assetDescHash`.
2. **Grammar.** `asset_desc` parses under section 3.
3. **Manifest hash**, full form only: `BLAKE2b-256(JCS(M))` equals
   `content-hash`. The CID MAY additionally be checked.
4. **Cross-field consistency.** `M.schema_version` is `zmd1`;
   `M.collection.slug` equals the descriptor's collection; `M.item.index`
   equals the descriptor's index; `M.collection.issuer_vk` equals `ik`;
   `M.collection.network` equals the chain's network.
5. **Creator signature** verifies over `signing_digest` under `ik`.
6. **Media integrity** for every media object whose bytes were fetched.

Step 1 MUST precede step 3. A verifier that canonicalizes and hashes a manifest
before comparing the cheap 32-byte value gives an attacker a free amplification
primitive.

The outcome is `VERIFIED(FULL)`, `VERIFIED(MINIMAL)` or `INVALID`. Clients MUST
distinguish the two successful outcomes. On `INVALID` a client MUST NOT
partially trust the bundle, for example by showing its name while discarding its
media.

A verifier that omits step 5 MUST report that it did so. In the minimal form the
signature is the only thing backing the manifest.

## 6. Storage

ZMD-1 is transport-agnostic. Because every media object is bound by hash, where
bytes come from has no bearing on whether they are authentic, only on whether
they are available.

Availability is an operational commitment and not a cryptographic one. Nothing
in this specification keeps bytes alive.

## 7. Extension

A future revision MUST use a different tag. A parser encountering an unknown tag
MUST NOT interpret the descriptor under this specification.

Unknown members inside a manifest are permitted and MUST be preserved when
hashing, so a newer issuer and an older verifier agree on the content hash even
when the verifier does not understand every field.

## 8. Security considerations

**Homoglyphs.** The descriptor grammar excludes case, whitespace and non-ASCII
characters precisely so that two visually similar collections cannot exist.
Manifest display names carry no such restriction, so clients SHOULD present the
slug or the asset identity, not only the display name.

**Network replay.** `collection.network` exists because an issuer using the same
key and description on two networks produces the same identity on both. Step 4
is what stops a test-network manifest being presented against a mainnet asset.

**Metadata availability.** Section 6. A verifiable identity for an unresolvable
object is a real failure mode and this specification does not address it.

**Signature scope.** The creator signature covers the manifest, not the media
bytes. Media is bound by hash through the manifest, so tampering with media is
caught at step 6 rather than step 5.

**Index reuse.** Section 3.2. The protocol does not enforce uniqueness of
`(collection, index)`; clients must.

## 9. References

- ZIP 227, Issuance of Zcash Shielded Assets
- ZIP 226, Transfer and Burn of Zcash Shielded Assets
- RFC 8785, JSON Canonicalization Scheme
- RFC 2119, Key words for use in RFCs to Indicate Requirement Levels
- BIP-340, Schnorr Signatures for secp256k1
- Multiformats: CIDv1, multibase, multicodec, multihash
