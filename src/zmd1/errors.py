"""Exception types raised by this package."""

from __future__ import annotations


class Zmd1Error(Exception):
    """Base class for every error raised by this package."""


class Invalid(Zmd1Error):
    """A bundle failed verification.

    Verification is all-or-nothing. A caller that catches this must discard the
    whole bundle rather than displaying part of it.
    """


class NodeError(Zmd1Error):
    """A Zcash node was reached and refused the request."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class NodeUnreachable(Zmd1Error):
    """A Zcash node could not be reached at all."""


class SchemaUnavailable(Zmd1Error):
    """The optional ``jsonschema`` dependency is not installed."""
