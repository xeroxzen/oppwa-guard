# Test your integration

This guide shows you how to turn each failure in the [threat model](../concepts/threat-model.md) into a regression test against your own handlers, without calling a real gateway.

## Generate encrypted notifications

`encrypt_notification_for_testing` produces a body, IV and tag the way OPPWA does, in hex. It isn't exported from the top-level package, so that nobody calls it in production by accident:

```python
import os
from oppwa_guard.webhook import encrypt_notification_for_testing

TEST_KEY = os.urandom(32).hex()

sealed = encrypt_notification_for_testing(
    TEST_KEY,
    {
        "type": "PAYMENT",
        "payload": {
            "id": "8ac7a4a1845f7e8b0184604b1d2b4c2e",
            "paymentType": "DB",
            "amount": "250.00",
            "currency": "USD",
            "merchantTransactionId": "ORD-2002",
            "result": {"code": "000.000.000", "description": "Transaction succeeded"},
        },
    },
)

response = client.post(
    "/webhooks/oppwa",
    content=sealed["body"],
    headers={
        "X-Initialization-Vector": sealed["iv"],
        "X-Authentication-Tag": sealed["tag"],
    },
)
```

Configure your app under test with `TEST_KEY` as its webhook secret.

## Tests worth writing

| Test | Send | Expect |
|---|---|---|
| Currency swap | A success response with `currency` different from the order | Order not fulfilled |
| Amount short | `amount` lower than the order | Order not fulfilled |
| Wrong order | `merchantTransactionId` of another order | Order not fulfilled |
| Test-mode code | `result.code` = `000.100.110` | Order not fulfilled |
| Edited return | Shopper return whose `resourcePath` points at another checkout | Status fetched for the stored checkout; tampering logged |
| Duplicate delivery | The same sealed notification 10 times concurrently | Order credited once |
| Tampered notification | Flip one hex character of `body` | `400`, nothing credited |

For the duplicate test, send the requests concurrently, for example with `asyncio.gather`. Sequential requests won't expose a check-then-act race.

## What's next

- Review the [result codes](../reference/result-codes.md) your acquirer documents, and add a test for any extra codes it uses.
