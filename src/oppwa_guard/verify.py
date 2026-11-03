"""Verify a payment status response against the order the merchant actually created.

A success result code only says *a* payment succeeded. Fulfilment is safe only when
that payment is bound to this order, for this amount, in this currency.
"""

from __future__ import annotations

import enum
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from oppwa_guard.result_codes import Outcome, classify

_CURRENCY = re.compile(r"^[A-Z]{3}$")
_TWO_PLACES = Decimal("0.01")


class Rejection(enum.Enum):
    MALFORMED = "malformed_response"
    NOT_SUCCESSFUL = "not_successful"
    PENDING = "pending"
    NEEDS_REVIEW = "needs_manual_review"
    TEST_MODE = "test_mode_result_in_live_check"
    ORDER_MISMATCH = "merchant_transaction_id_mismatch"
    PAYMENT_TYPE_MISMATCH = "payment_type_mismatch"
    CURRENCY_MISMATCH = "currency_mismatch"
    AMOUNT_MISMATCH = "amount_mismatch"


@dataclass(frozen=True)
class ExpectedPayment:
    """What the merchant's own database says the customer must pay."""

    merchant_transaction_id: str
    amount: Decimal
    currency: str
    payment_type: str = "DB"

    def __post_init__(self) -> None:
        if not self.merchant_transaction_id:
            raise ValueError("merchant_transaction_id is required")
        if not _CURRENCY.match(self.currency):
            raise ValueError(f"currency must be an ISO 4217 code, got {self.currency!r}")
        if self.amount <= 0 or self.amount != self.amount.quantize(_TWO_PLACES):
            raise ValueError(f"amount must be positive with at most 2 decimals, got {self.amount}")


@dataclass(frozen=True)
class Verdict:
    accepted: bool
    reason: Rejection | None
    detail: str
    payment_id: str | None


def _text(mapping: Mapping[str, object], key: str) -> str | None:
    value = mapping.get(key)
    return value if isinstance(value, str) else None


def _reject(reason: Rejection, detail: str, payment_id: str | None) -> Verdict:
    return Verdict(accepted=False, reason=reason, detail=detail, payment_id=payment_id)


def _check_outcome(code: str, allow_test_mode: bool) -> tuple[Rejection, str] | None:
    outcome = classify(code)
    if outcome is Outcome.SUCCESS:
        return None
    if outcome is Outcome.TEST_MODE_SUCCESS:
        return None if allow_test_mode else (Rejection.TEST_MODE, f"test-mode code {code}")
    if outcome is Outcome.SUCCESS_NEEDS_REVIEW:
        return Rejection.NEEDS_REVIEW, f"code {code} requires manual review"
    if outcome is Outcome.PENDING:
        return Rejection.PENDING, f"code {code} is pending"
    return Rejection.NOT_SUCCESSFUL, f"code {code} is not a success"


def _check_binding(
    expected: ExpectedPayment, response: Mapping[str, object]
) -> tuple[Rejection, str] | None:
    order_ref = _text(response, "merchantTransactionId")
    if order_ref != expected.merchant_transaction_id:
        return Rejection.ORDER_MISMATCH, (
            f"payment belongs to {order_ref!r}, not {expected.merchant_transaction_id!r}"
        )
    payment_type = _text(response, "paymentType")
    if payment_type != expected.payment_type:
        return Rejection.PAYMENT_TYPE_MISMATCH, (
            f"paymentType {payment_type!r}, expected {expected.payment_type!r}"
        )
    currency = _text(response, "currency")
    if currency != expected.currency:
        return Rejection.CURRENCY_MISMATCH, f"paid in {currency!r}, invoiced in {expected.currency}"
    amount_text = _text(response, "amount") or ""
    try:
        amount = Decimal(amount_text)
    except InvalidOperation:
        return Rejection.MALFORMED, f"unparseable amount {amount_text!r}"
    if amount != expected.amount:
        return Rejection.AMOUNT_MISMATCH, f"paid {amount}, invoiced {expected.amount}"
    return None


def verify_payment(
    expected: ExpectedPayment,
    response: Mapping[str, object],
    *,
    allow_test_mode: bool = False,
) -> Verdict:
    """Decide whether ``response`` pays for ``expected``.

    ``response`` is an OPPWA payment-status body or a notification payload. Only fulfil
    the order when ``Verdict.accepted`` is True.
    """
    payment_id = _text(response, "id")
    result = response.get("result")
    code = _text(result, "code") if isinstance(result, Mapping) else None
    if payment_id is None or code is None:
        return _reject(Rejection.MALFORMED, "response lacks id or result.code", payment_id)
    try:
        failure = _check_outcome(code, allow_test_mode)
    except ValueError as exc:
        return _reject(Rejection.MALFORMED, str(exc), payment_id)
    if failure is None:
        failure = _check_binding(expected, response)
    if failure is not None:
        return _reject(failure[0], failure[1], payment_id)
    return Verdict(accepted=True, reason=None, detail=f"code {code}", payment_id=payment_id)
