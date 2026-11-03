# Get started

This guide shows you how to install oppwa-guard and use it to decide whether a payment pays for an order. It takes about five minutes.

## Before you begin

- Python 3.10 or later.
- [uv](https://docs.astral.sh/uv/) to manage the project.
- An OPPWA integration that creates checkouts with a `merchantTransactionId`. If you don't send one yet, see [Bind each checkout to an order](#bind-each-checkout-to-an-order).

## Install the package

```bash
uv add oppwa-guard
```

## Verify a payment

1. Load the order from your own database. Don't use anything the browser sent you.

2. Describe what the customer must pay:

   ```python
   from decimal import Decimal
   from oppwa_guard import ExpectedPayment

   expected = ExpectedPayment(
       merchant_transaction_id=order.id,
       amount=Decimal(order.amount),  # for example Decimal("1000.00")
       currency=order.currency,  # ISO 4217, for example "USD"
   )
   ```

   `ExpectedPayment` raises `ValueError` if the amount isn't positive with at most two decimal places, or if the currency isn't three capital letters. These are bugs in your code, so let them surface.

3. Pass the gateway's payment-status body to `verify_payment`:

   ```python
   from oppwa_guard import verify_payment

   verdict = verify_payment(expected, response.json())
   ```

4. Act on the verdict:

   ```python
   if verdict.accepted:
       fulfil_once(order, verdict.payment_id)
   else:
       log.info("not fulfilling %s: %s (%s)", order.id, verdict.reason, verdict.detail)
   ```

`verify_payment` never raises on a bad response. A response that is missing fields or has an unparseable amount comes back as a rejected verdict with the reason `Rejection.MALFORMED`.

## Try it

Run this in `uv run python` to see a currency swap being rejected:

```python
from decimal import Decimal
from oppwa_guard import ExpectedPayment, verify_payment

expected = ExpectedPayment("ORD-1001", Decimal("1000.00"), "USD")
response = {
    "id": "8ac7a4a1845f7e8b0184604b1d2b4c2e",
    "paymentType": "DB",
    "amount": "1000.00",
    "currency": "ZWG",
    "merchantTransactionId": "ORD-1001",
    "result": {"code": "000.000.000", "description": "Transaction succeeded"},
}
print(verify_payment(expected, response))
```

Output:

```text
Verdict(accepted=False, reason=<Rejection.CURRENCY_MISMATCH: 'currency_mismatch'>, detail="paid in 'ZWG', invoiced in USD", payment_id='8ac7a4a1845f7e8b0184604b1d2b4c2e')
```

The result code says success. The verdict says no, because the payment was made in the wrong currency.

## Bind each checkout to an order

`verify_payment` compares the response's `merchantTransactionId` with your order. That only works if you send it when you create the checkout:

```python
gateway.post(
    "/v1/checkouts",
    data={
        "entityId": ENTITY_ID,
        "amount": "1000.00",
        "currency": "USD",
        "paymentType": "DB",
        "merchantTransactionId": order.id,
    },
)
```

Store the checkout `id` the gateway returns against the order. You need it to [verify the shopper return](how-to/verify-shopper-return.md).

## What's next

- [Verify a shopper return](how-to/verify-shopper-return.md) without trusting `resourcePath`.
- [Handle webhook notifications](how-to/handle-webhooks.md).
- [Credit each payment exactly once](how-to/credit-exactly-once.md). Verification alone doesn't stop duplicates.
