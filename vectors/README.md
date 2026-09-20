# Conformance vectors

Machine-readable test vectors for independent ZMD-1 implementations. Every file
here is consumed by this repository's own test suite, so it cannot drift from
the reference implementation without turning the build red.

| File | Covers |
|---|---|
| `descriptors.json` | descriptor grammar: 6 accepted, 16 rejected with the reason |
| `canonicalization.json` | RFC 8785 output, BLAKE2b-256 digest and CIDv1 for 7 documents |
| `manifest.json` | one worked item end to end: canonical bytes, content hash, signing digest, media hash, both descriptor forms |

All hashes are BLAKE2b-256, lowercase hex. CIDs are CIDv1, `raw` multicodec,
sha2-256 multihash, base32 lowercase.

The `invalid` entries in `descriptors.json` matter more than the valid ones. An
implementation that accepts any of them will produce asset identities that
another implementation reads differently.
