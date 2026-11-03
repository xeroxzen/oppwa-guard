from __future__ import annotations

from decimal import Decimal

import pytest

from oppwa_guard import ExpectedPayment, Outcome, Rejection, classify, verify_payment

ORDER = ExpectedPayment(
    merchant_transaction_id="ORD-1001", amount=Decimal("1000.00"), currency="USD"
)


def status(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "8ac7a4a1845f7e8b0184604b1d2b4c2e",
        "paymentType": "DB",
        "amount": "1000.00",
        "currency": "USD",
        "merchantTransactionId": "ORD-1001",
        "result": {"code": "000.000.000", "description": "Transaction succeeded"},
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    ("code", "outcome"),
    [
        ("000.000.000", Outcome.SUCCESS),
        ("000.100.110", Outcome.TEST_MODE_SUCCESS),
        ("000.100.112", Outcome.TEST_MODE_SUCCESS),
        ("000.400.110", Outcome.SUCCESS),
        ("000.400.100", Outcome.SUCCESS_NEEDS_REVIEW),
        ("000.400.030", Outcome.REJECTED),
        ("000.200.000", Outcome.PENDING),
        ("000.200.100", Outcome.PENDING),
        ("800.400.500", Outcome.PENDING),
        ("100.396.101", Outcome.REJECTED),
        ("800.100.151", Outcome.REJECTED),
    ],
)
def test_classify(code: str, outcome: Outcome) -> None:
    assert classify(code) is outcome


def test_classify_rejects_malformed_code() -> None:
    with pytest.raises(ValueError, match="not an OPPWA result code"):
        classify("000.000")


def test_accepts_matching_payment() -> None:
    verdict = verify_payment(ORDER, status())
    assert verdict.accepted
    assert verdict.payment_id == "8ac7a4a1845f7e8b0184604b1d2b4c2e"


def test_currency_swap_is_rejected() -> None:
    verdict = verify_payment(ORDER, status(currency="ZWG"))
    assert verdict.reason is Rejection.CURRENCY_MISMATCH


def test_amount_mismatch_is_rejected() -> None:
    assert verify_payment(ORDER, status(amount="10.00")).reason is Rejection.AMOUNT_MISMATCH


def test_amount_compared_as_decimal_not_string() -> None:
    assert verify_payment(ORDER, status(amount="1000.0")).accepted


def test_payment_for_another_order_is_rejected() -> None:
    verdict = verify_payment(ORDER, status(merchantTransactionId="ORD-9999"))
    assert verdict.reason is Rejection.ORDER_MISMATCH


def test_missing_order_reference_is_rejected() -> None:
    response = status()
    del response["merchantTransactionId"]
    assert verify_payment(ORDER, response).reason is Rejection.ORDER_MISMATCH


def test_preauthorisation_is_not_a_debit() -> None:
    assert verify_payment(ORDER, status(paymentType="PA")).reason is Rejection.PAYMENT_TYPE_MISMATCH


def test_test_mode_code_rejected_unless_allowed() -> None:
    response = status(result={"code": "000.100.110"})
    assert verify_payment(ORDER, response).reason is Rejection.TEST_MODE
    assert verify_payment(ORDER, response, allow_test_mode=True).accepted


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        ("000.200.000", Rejection.PENDING),
        ("000.400.100", Rejection.NEEDS_REVIEW),
        ("800.100.151", Rejection.NOT_SUCCESSFUL),
        ("garbage", Rejection.MALFORMED),
    ],
)
def test_non_success_codes(code: str, reason: Rejection) -> None:
    assert verify_payment(ORDER, status(result={"code": code})).reason is reason


def test_malformed_responses() -> None:
    assert verify_payment(ORDER, {}).reason is Rejection.MALFORMED
    assert verify_payment(ORDER, status(result="ok")).reason is Rejection.MALFORMED
    assert verify_payment(ORDER, status(amount="1,000.00")).reason is Rejection.MALFORMED


@pytest.mark.parametrize(
    ("amount", "currency"),
    [
        (Decimal("0"), "USD"),
        (Decimal("1.001"), "USD"),
        (Decimal("10"), "usd"),
        (Decimal("10"), "US"),
    ],
)
def test_expected_payment_validates_inputs(amount: Decimal, currency: str) -> None:
    with pytest.raises(ValueError):
        ExpectedPayment(merchant_transaction_id="ORD-1", amount=amount, currency=currency)
