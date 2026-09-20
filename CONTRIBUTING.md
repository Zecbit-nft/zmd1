# Contributing

## Setup

```bash
pip install -e ".[dev]"
pytest -q
ruff check . && ruff format --check .
mypy
```

CI runs the suite on Python 3.9 through 3.13, plus lint and type checks. All of
it must pass.

## Changing the specification

`SPEC.md` is normative. A change to it is a change to what asset identities
mean, so:

- Anything that alters a hash, a digest or the grammar is a breaking change and
  needs a new tag, not a new version of `zmd1`. See SPEC.md section 7.
- Add conformance vectors for the new behaviour in the same pull request. The
  vectors are consumed by the test suite; a vector that disagrees with the
  implementation turns CI red, which is the point.
- Rejection cases matter more than acceptance cases. An implementation that
  wrongly accepts a malformed descriptor produces asset identities that other
  implementations read differently.

## Style

The code carries no inline comments. Where something is not obvious from the
code, it belongs in a docstring, in `SPEC.md`, or in `README.md` — somewhere a
reader who is not reading the source can find it.

Line length is 100. `ruff format` decides layout; do not argue with it.

## Reporting a problem

A verification bug is a security issue if it causes a bundle to be accepted that
should be rejected. See [SECURITY.md](SECURITY.md).
