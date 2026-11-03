"""Decrypt OPPWA webhook notifications (AES-256-GCM).

OPPWA sends the ciphertext as the request body and the IV and authentication tag in the
``X-Initialization-Vector`` and ``X-Authentication-Tag`` headers. The common format is
hex for the key, body, IV and tag. Some acquirers use Base64, so confirm the encoding
your acquirer uses and pass ``encoding="base64"`` if needed.

GCM authentication means a successful decrypt proves the notification came from a holder
of the key. It does not prove the notification is new. Replays decrypt fine, so
idempotency (see ``oppwa_guard.idempotency``) is still required.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
from collections.abc import Mapping
from typing import Literal

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

Encoding = Literal["hex", "base64"]
_KEY_BYTES = 32
_TAG_BYTES = 16
_MIN_IV_BYTES = 8
_MAX_IV_BYTES = 128


class NotificationError(Exception):
    """The notification could not be authenticated or parsed. Respond non-2xx and do nothing."""


def _decode(value: str | bytes, encoding: Encoding) -> bytes:
    raw = value.strip() if isinstance(value, bytes) else value.strip().encode("ascii")
    try:
        return (
            binascii.unhexlify(raw) if encoding == "hex" else base64.b64decode(raw, validate=True)
        )
    except (binascii.Error, ValueError) as exc:
        raise NotificationError(f"invalid {encoding} input") from exc


def decrypt_notification(
    key: str,
    iv: str,
    tag: str,
    body: str | bytes,
    *,
    encoding: Encoding = "hex",
) -> dict[str, object]:
    """Authenticate and decrypt a notification. Raises NotificationError on any failure."""
    key_bytes = binascii.unhexlify(key) if encoding == "hex" else base64.b64decode(key)
    if len(key_bytes) != _KEY_BYTES:
        raise ValueError("webhook secret must be 256 bits")
    tag_bytes = _decode(tag, encoding)
    if len(tag_bytes) != _TAG_BYTES:
        raise NotificationError("authentication tag must be 128 bits")
    iv_bytes = _decode(iv, encoding)
    if not _MIN_IV_BYTES <= len(iv_bytes) <= _MAX_IV_BYTES:
        raise NotificationError("initialisation vector has an invalid length")
    ciphertext = _decode(body, encoding) + tag_bytes
    try:
        plaintext = AESGCM(key_bytes).decrypt(iv_bytes, ciphertext, None)
    except InvalidTag as exc:
        raise NotificationError("authentication failed") from exc
    try:
        parsed = json.loads(plaintext)
    except json.JSONDecodeError as exc:
        raise NotificationError("decrypted body is not JSON") from exc
    if not isinstance(parsed, dict):
        raise NotificationError("decrypted body is not a JSON object")
    return parsed


def payment_payload(notification: Mapping[str, object]) -> Mapping[str, object]:
    """Return the payment object from a decrypted notification of type PAYMENT."""
    if notification.get("type") != "PAYMENT":
        raise NotificationError(f"not a PAYMENT notification: {notification.get('type')!r}")
    payload = notification.get("payload")
    if not isinstance(payload, Mapping):
        raise NotificationError("notification has no payload object")
    return payload


def encrypt_notification_for_testing(
    key_hex: str, notification: Mapping[str, object]
) -> dict[str, str]:
    """Produce hex body/iv/tag the way OPPWA does. For tests and local simulators only."""
    iv = os.urandom(12)
    sealed = AESGCM(binascii.unhexlify(key_hex)).encrypt(
        iv, json.dumps(notification).encode("utf-8"), None
    )
    return {
        "body": sealed[:-_TAG_BYTES].hex(),
        "iv": iv.hex(),
        "tag": sealed[-_TAG_BYTES:].hex(),
    }
