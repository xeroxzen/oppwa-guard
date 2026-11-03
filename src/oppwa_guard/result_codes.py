"""Classify OPPWA result codes.

Patterns follow the OPPWA result-code reference. Codes matching ``000.100.1`` are
successes in *integrator test mode*; a live integration must never fulfil on them,
so they get their own outcome instead of being folded into SUCCESS.
"""

from __future__ import annotations

import enum
import re

_CODE_SHAPE = re.compile(r"^\d{3}\.\d{3}\.\d{3}$")
_TEST_MODE_SUCCESS = re.compile(r"^000\.100\.1")
_SUCCESS = re.compile(r"^(000\.000\.|000\.[36]|000\.400\.1[12]0|000\.500\.)")
_SUCCESS_NEEDS_REVIEW = re.compile(r"^(000\.400\.0[^3]|000\.400\.100)")
_PENDING = re.compile(r"^(000\.200|800\.400\.5|100\.400\.500)")


class Outcome(enum.Enum):
    SUCCESS = "success"
    TEST_MODE_SUCCESS = "test_mode_success"
    SUCCESS_NEEDS_REVIEW = "success_needs_review"
    PENDING = "pending"
    REJECTED = "rejected"


def classify(code: str) -> Outcome:
    """Map an OPPWA ``result.code`` to an Outcome. Raises ValueError on a malformed code."""
    if not _CODE_SHAPE.match(code):
        raise ValueError(f"not an OPPWA result code: {code!r}")
    if _TEST_MODE_SUCCESS.match(code):
        return Outcome.TEST_MODE_SUCCESS
    if _SUCCESS.match(code):
        return Outcome.SUCCESS
    if _SUCCESS_NEEDS_REVIEW.match(code):
        return Outcome.SUCCESS_NEEDS_REVIEW
    if _PENDING.match(code):
        return Outcome.PENDING
    return Outcome.REJECTED
