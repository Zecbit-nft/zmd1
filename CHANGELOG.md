# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0]

First release.

### Added

- Descriptor grammar with minimal and full forms, parsing and construction.
- `assetDescHash` derivation per ZIP 227, personalized `ZSA-AssetDescCRH`.
- RFC 8785 canonicalization over the subset ZMD-1 permits, with UTF-16 code
  unit key ordering and 53-bit integer enforcement.
- CIDv1 encoding and decoding, `raw` multicodec, base32 lowercase, sha2-256 and
  blake2b-256 multihashes.
- Manifest content hash, creator signing digest and media hash.
- The six-step verification algorithm with pluggable signature verification.
- JSON Schema for the item manifest, with optional validation via `zmd1[schema]`.
- JSON-RPC client for checking descriptors against a Zcash node.
- `zmd1` command line interface.
- Conformance vectors under `vectors/`, consumed by the test suite.
