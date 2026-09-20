# Security

## Reporting

Report suspected vulnerabilities through GitHub's private advisory form on this
repository, or to security@zecbit.io. Please do not open a public issue first.

## What counts

A bundle that `verify()` accepts and the specification says it should reject is
a vulnerability. So is a manifest that two conformant implementations
canonicalize to different bytes.

Availability of metadata or media is out of scope: ZMD-1 binds bytes, it does
not store them. See SPEC.md section 6.

## Scope of this implementation

Signature verification is supplied by the caller. This package computes the
signing digest and does not implement BIP-340. A caller that passes no verifier
gets `signature_checked = False`, and in the minimal form that means nothing has
been checked about the manifest's authorship.

This code has not been independently audited.
