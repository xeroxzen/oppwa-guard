"""Handle the ``resourcePath`` that OPPWA appends to the shopper result URL.

The shopper's browser delivers ``resourcePath``, so the shopper controls it. Never build
the status request from it. Build the path from the checkout id stored server-side, and
treat a mismatched ``resourcePath`` as a tampering signal worth logging.
"""

from __future__ import annotations

import re

_CHECKOUT_ID = re.compile(r"^[A-Za-z0-9.\-]{1,128}$")


def status_path(stored_checkout_id: str) -> str:
    """Return the payment-status path for a checkout id taken from the merchant's own store."""
    if not _CHECKOUT_ID.match(stored_checkout_id):
        raise ValueError(f"invalid checkout id: {stored_checkout_id!r}")
    return f"/v1/checkouts/{stored_checkout_id}/payment"


def resource_path_matches(resource_path: str, stored_checkout_id: str) -> bool:
    """True when the browser-supplied resourcePath points at the stored checkout."""
    return resource_path == status_path(stored_checkout_id)
