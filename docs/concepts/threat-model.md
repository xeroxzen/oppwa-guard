# Threat model

This page explains the four integration failures oppwa-guard is designed to prevent, who can exploit each one, and which part of the library closes it.

None of these failures needs broken cryptography or access to the gateway. Each one is a merchant handler that trusts something it shouldn't.

## Who the attacker is

The attacker is a shopper, or someone acting as one. They can:

- Create checkouts and pay with any currency or card the gateway accepts.
- Edit any URL their browser visits, including the shopper result URL.
- Replay or delay requests their browser sends.

They can't read your gateway credentials or your webhook secret. If they can, you have a bigger problem than this library solves.

## Failure 1: A success code without a binding

**What happens.** The handler checks `result.code`, sees `000.000.000`, and ships the order.

**Why it's wrong.** A result code describes one payment. It says nothing about which order that payment was for, how much it was for, or in which currency. If your gateway entity accepts more than one currency, a shopper can pay a USD 1,000 order with ZWG 1,000 and the code is still `000.000.000`.

**The fix.** [`verify_payment`](../reference/api.md#verify_payment) compares the response's `merchantTransactionId`, `paymentType`, `currency` and `amount` with what your own database says. All four must match.

## Failure 2: Trusting `resourcePath`

**What happens.** After payment, OPPWA redirects the shopper to your result URL with a `resourcePath` query parameter. The handler requests `GET {resourcePath}` from the gateway and fulfils on the answer.

**Why it's wrong.** The shopper's browser delivers `resourcePath`, so the shopper controls it. They can replace it with the path of a different, successful payment, such as a small payment they made earlier. Depending on how the URL is joined, they may even point it at a server they control.

**The fix.** Build the path yourself with [`status_path`](../reference/api.md#status_path) from the checkout id you stored when you created the checkout. Use [`resource_path_matches`](../reference/api.md#resource_path_matches) only to log a mismatch as a tampering signal.

## Failure 3: Test mode in production

**What happens.** An entity configured for integrator test mode returns codes such as `000.100.110` ("Request successfully processed in 'Merchant in Integrator Test Mode'"). A handler that treats every `000.` code as success fulfils orders whose money never moves.

**The fix.** [`classify`](../reference/api.md#classify) returns `Outcome.TEST_MODE_SUCCESS` for these codes, and `verify_payment` rejects them unless you pass `allow_test_mode=True`. Never pass that in production.

## Failure 4: Crediting more than once

**What happens.** The handler checks "have I processed this payment?", then credits the order. Two deliveries of the same notification arrive at once. Both pass the check before either writes. The order is credited twice.

Duplicates are normal, not an attack. Gateways retry notifications that time out, and the shopper redirect and the webhook often arrive within milliseconds of each other. An attacker who captures one encrypted notification can also replay it: AES-GCM proves who sent it, not that it's new.

**Why a lock doesn't fix it.** An in-process lock protects one worker. Production runs several workers, often on several servers.

**The fix.** [`claim_payment`](../reference/api.md#claim_payment) inserts the payment id into a table with a primary key, inside the transaction that credits the order. The database lets exactly one insert succeed. See [Credit each payment exactly once](../how-to/credit-exactly-once.md).

## Out of scope

- Card fraud, chargebacks and 3-D Secure decisions. Those belong to the gateway and acquirer.
- Securing your gateway credentials and webhook secret.
- Network-level attacks on the connection to the gateway. Use HTTPS with certificate verification.
- Acquirer-specific result codes not in the public OPPWA reference.

## See also

- [Result codes](../reference/result-codes.md)
- [Test your integration](../how-to/test-your-integration.md), which turns each failure into a regression test.
