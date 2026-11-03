# Troubleshooting

## Every payment is rejected with `ORDER_MISMATCH`

The response's `merchantTransactionId` doesn't equal `ExpectedPayment.merchant_transaction_id`.

- Check that you send `merchantTransactionId` when you create the checkout. Without it, the response has no value to compare and every payment is rejected.
- Check you pass the same string both times. `"1001"` and `"ORD-1001"` don't match.

## Every payment is rejected with `TEST_MODE`

Your entity is in integrator test mode and returns `000.100.110`. Against a test entity, pass `allow_test_mode=True`. If you see this in production, your entity or credentials are misconfigured. Fix the configuration rather than allowing test mode.

## `AMOUNT_MISMATCH` when the amounts look equal

The comparison is exact on decimal value, so `"250"` and `"250.00"` match, but `"250.00"` and `"249.99"` don't. Check whether a fee, discount or currency conversion was applied after you stored the order amount. If the gateway amount includes a surcharge, store the amount you expect the gateway to report.

## `ExpectedPayment` raises `ValueError: amount must be positive with at most 2 decimals`

You probably passed a float. `Decimal(19.99)` is `19.989999999999998436805981327779591083526611328125`. Build the `Decimal` from a string or from your database's decimal type: `Decimal("19.99")`.

## `NotificationError: authentication failed` on every webhook

- The secret is wrong. Copy it again from the gateway dashboard; it's 64 hex characters.
- The encoding is wrong. Try `encoding="base64"` if your acquirer documents Base64.
- The body was modified before you read it. Pass the raw bytes. Don't decode, strip or re-serialise JSON first. Some frameworks parse the body when you access it as JSON, so read it as raw data.

## `ValueError: webhook secret must be 256 bits`

The key isn't 32 bytes after decoding. A hex key is 64 characters. Check for a truncated environment variable or surrounding quotes.

## `claim_payment` returns `False` for a payment that was never credited

A claim was committed without the matching credit. That happens when the claim and the credit run in separate transactions. Put both in one transaction, as shown in [Credit each payment exactly once](how-to/credit-exactly-once.md), then delete the orphaned row from `processed_payments` after confirming the payment with the gateway.
