# Verify a shopper return

After payment, OPPWA redirects the shopper to your `shopperResultUrl` with `id` and `resourcePath` query parameters. This guide shows you how to check the payment without trusting either of them.

## Before you begin

- You send `merchantTransactionId` when you create the checkout.
- You store the checkout `id` the gateway returns against the order.

## Steps

1. Identify the order from your own session or URL, not from `resourcePath`. A common pattern is to put your order id in the `shopperResultUrl`, for example `https://shop.example/return/ORD-1001`.

2. Load the stored checkout id and compare it with what the browser sent. A mismatch doesn't stop the flow, because you never use the browser's value, but it's worth recording:

   ```python
   from oppwa_guard import resource_path_matches

   order = db.load_order(order_id)
   if not resource_path_matches(request.args.get("resourcePath", ""), order.checkout_id):
       security_log.warning("resourcePath tampering on order %s", order.id)
   ```

3. Build the status path from the stored checkout id and call the gateway:

   ```python
   from oppwa_guard import status_path

   response = gateway.get(
       status_path(order.checkout_id),
       params={"entityId": ENTITY_ID},
       timeout=10,
   )
   ```

   `status_path` returns `/v1/checkouts/{id}/payment`. It raises `ValueError` if the stored id contains anything other than letters, digits, dots and hyphens, which would mean your own store is corrupted.

4. Verify the payment against the order:

   ```python
   from decimal import Decimal
   from oppwa_guard import ExpectedPayment, Rejection, verify_payment

   verdict = verify_payment(
       ExpectedPayment(order.id, Decimal(order.amount), order.currency),
       response.json(),
   )
   ```

5. Decide what to show the shopper:

   ```python
   if verdict.accepted:
       fulfil_once(order, verdict.payment_id)
       return render("thank_you.html")
   if verdict.reason is Rejection.PENDING:
       return render("processing.html")  # the webhook will finish the job
   return render("payment_failed.html")
   ```

> [!IMPORTANT]
> `fulfil_once` must use [`claim_payment`](credit-exactly-once.md). The shopper return and the webhook for the same payment often arrive at the same moment.

## Why not use `resourcePath`?

The shopper's browser delivers it, so the shopper can change it to the path of a different successful payment. See [Failure 2 in the threat model](../concepts/threat-model.md#failure-2-trusting-resourcepath).

## What's next

- [Handle webhook notifications](handle-webhooks.md) so pending payments are completed even if the shopper closes the tab.
