from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

import pytest

from oppwa_guard import (
    NotificationError,
    claim_payment,
    decrypt_notification,
    ensure_schema,
    payment_payload,
    resource_path_matches,
    status_path,
)
from oppwa_guard.webhook import encrypt_notification_for_testing

KEY = os.urandom(32).hex()
NOTIFICATION = {"type": "PAYMENT", "payload": {"id": "pay-1", "result": {"code": "000.000.000"}}}


def test_round_trip_decrypt() -> None:
    sealed = encrypt_notification_for_testing(KEY, NOTIFICATION)
    decrypted = decrypt_notification(KEY, sealed["iv"], sealed["tag"], sealed["body"])
    assert payment_payload(decrypted)["id"] == "pay-1"


def test_tampered_body_fails_authentication() -> None:
    sealed = encrypt_notification_for_testing(KEY, NOTIFICATION)
    flipped = ("0" if sealed["body"][0] != "0" else "1") + sealed["body"][1:]
    with pytest.raises(NotificationError, match="authentication failed"):
        decrypt_notification(KEY, sealed["iv"], sealed["tag"], flipped)


def test_wrong_key_fails_authentication() -> None:
    sealed = encrypt_notification_for_testing(KEY, NOTIFICATION)
    with pytest.raises(NotificationError):
        decrypt_notification(os.urandom(32).hex(), sealed["iv"], sealed["tag"], sealed["body"])


def test_non_hex_input_is_a_notification_error() -> None:
    with pytest.raises(NotificationError, match="invalid hex"):
        decrypt_notification(KEY, "zz", "00" * 16, "00")


@pytest.mark.parametrize("iv", ["", "abcd", "00" * 129])
def test_bad_iv_length_is_a_notification_error(iv: str) -> None:
    with pytest.raises(NotificationError, match="initialisation vector"):
        decrypt_notification(KEY, iv, "00" * 16, "00")


def test_short_key_is_a_configuration_error() -> None:
    with pytest.raises(ValueError, match="256 bits"):
        decrypt_notification("00" * 16, "00" * 12, "00" * 16, "00")


def test_non_payment_notification_rejected() -> None:
    with pytest.raises(NotificationError, match="not a PAYMENT"):
        payment_payload({"type": "REGISTRATION", "payload": {}})


def test_status_path_uses_stored_id() -> None:
    assert status_path("8ac7a4c9.uat01-vm-tx01") == "/v1/checkouts/8ac7a4c9.uat01-vm-tx01/payment"


@pytest.mark.parametrize("bad", ["", "../admin", "abc/def", "abc?x=1"])
def test_status_path_rejects_unsafe_ids(bad: str) -> None:
    with pytest.raises(ValueError):
        status_path(bad)


def test_resource_path_tampering_detected() -> None:
    assert resource_path_matches("/v1/checkouts/CHK1/payment", "CHK1")
    assert not resource_path_matches("/v1/checkouts/CHK2/payment", "CHK1")
    assert not resource_path_matches("/v1/attacker-mock-paid", "CHK1")


def test_claim_payment_is_exactly_once_across_connections(tmp_path: Path) -> None:
    db = tmp_path / "payments.db"
    with sqlite3.connect(db) as setup:
        ensure_schema(setup)
    winners: list[bool] = []
    guard = threading.Lock()
    start = threading.Barrier(12)

    def worker() -> None:
        conn = sqlite3.connect(db, timeout=10)
        try:
            start.wait()
            with conn:
                won = claim_payment(conn, "pay-1")
            with guard:
                winners.append(won)
        finally:
            conn.close()

    threads = [threading.Thread(target=worker) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert len(winners) == 12
    assert winners.count(True) == 1


def test_claim_rolled_back_with_failed_credit() -> None:
    conn = sqlite3.connect(":memory:")
    ensure_schema(conn)
    with pytest.raises(RuntimeError), conn:
        assert claim_payment(conn, "pay-1")
        raise RuntimeError("credit failed")
    with conn:
        assert claim_payment(conn, "pay-1"), "claim must roll back with the failed credit"
