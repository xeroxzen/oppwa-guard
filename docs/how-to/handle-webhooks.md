# Handle webhook notifications

OPPWA sends webhook notifications encrypted with AES-256-GCM. This guide shows you how to authenticate and decrypt them, then verify the payment they describe.

## Before you begin

- Your webhook is configured in the gateway's dashboard, and you have its secret: 64 hexadecimal characters (256 bits).
- You know which encoding your acquirer uses for the body, IV and tag. Hex is the common format. Some acquirers use Base64.

Keep the secret out of source control. Load it from your secret store or an environment variable.

## How a notification is sent

| Part | Where it arrives |
|---|---|
| Ciphertext | Request body |
| Initialisation vector | `X-Initialization-Vector` header |
| Authentication tag | `X-Authentication-Tag` header |

The decrypted body is a JSON object with a `type` (for example `PAYMENT`) and a `payload` that has the same shape as a payment-status response.

## Steps

1. Read the raw body and both headers, then decrypt:

   ```python
   from oppwa_guard import NotificationError, decrypt_notification, payment_payload

   try:
       notification = decrypt_notification(
           WEBHOOK_SECRET_HEX,
           request.headers["X-Initialization-Vector"],
           request.headers["X-Authentication-Tag"],
           request.get_data(),
       )
       payment = payment_payload(notification)
   except NotificationError:
       return "", 400
   ```

   If your acquirer uses Base64, pass `encoding="base64"`. The key must then be Base64 too.

2. Find the order the payment names, and verify it exactly as you would a shopper return:

   ```python
   from decimal import Decimal
   from oppwa_guard import ExpectedPayment, verify_payment

   order = db.find_order(payment.get("merchantTransactionId"))
   if order is None:
       security_log.warning("notification for unknown order")
       return "", 200
   verdict = verify_payment(
       ExpectedPayment(order.id, Decimal(order.amount), order.currency),
       payment,
   )
   ```

3. Credit once, then acknowledge:

   ```python
   if verdict.accepted:
       fulfil_once(order, verdict.payment_id)  # uses claim_payment
   return "", 200
   ```

## Which status code to return

| Situation | Return | Why |
|---|---|---|
| `NotificationError` | `400` | Not authentic or not parseable. Do nothing. |
| Authentic, any verdict | `200` | The gateway delivered it. A non-2xx response makes it retry, and a retry won't change the verdict. |
| Your database is down | `5xx` | You want the retry. |

## Things decryption doesn't prove

A successful decrypt proves the notification came from someone holding the secret. It doesn't prove:

- **That it's new.** A captured notification decrypts fine when replayed. [`claim_payment`](credit-exactly-once.md) handles that.
- **That it pays for the order.** Always run `verify_payment`.

## What's next

- [Credit each payment exactly once](credit-exactly-once.md).
- [Test your integration](test-your-integration.md) with encrypted notifications you generate yourself.
