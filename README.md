# oppwa-guard

Server-side payment verification for merchants that integrate an **OPPWA (Open Payment Platform)** checkout. Several acquirers and payment gateways across Africa and the Middle East expose OPPWA.

A success code tells you that *a* payment succeeded. It doesn't tell you that the payment is for this order, in this currency and for this amount, or that you haven't already credited it. oppwa-guard makes those checks explicit and hard to skip.

```python
from decimal import Decimal
from oppwa_guard import ExpectedPayment, verify_payment

verdict = verify_payment(
    ExpectedPayment("ORD-1001", Decimal("1000.00"), "USD"),
    gateway_response,
)
if verdict.accepted:
    fulfil(order)
```

## What it protects against

| Mistake | What it costs | Check |
|---|---|---|
| Fulfilling on a success code without checking currency and amount | An order invoiced at USD 1,000 is "paid" with ZWG 1,000 (about USD 35) | [`verify_payment`](https://github.com/xeroxzen/oppwa-guard/blob/main/docs/reference/api.md#verify_payment) |
| Building the status request from the browser's `resourcePath` | The shopper points your check at a payment that isn't theirs | [`status_path`](https://github.com/xeroxzen/oppwa-guard/blob/main/docs/reference/api.md#status_path) |
| Treating `000.100.110` as success in production | A test-mode entity accepts payments that never settle | [`classify`](https://github.com/xeroxzen/oppwa-guard/blob/main/docs/reference/api.md#classify) |
| Crediting on every notification delivery | Retries or replays credit one payment several times | [`claim_payment`](https://github.com/xeroxzen/oppwa-guard/blob/main/docs/reference/api.md#claim_payment) |

## Install

```bash
uv add oppwa-guard
```

Until the first PyPI release, install from GitHub instead: `uv add git+https://github.com/xeroxzen/oppwa-guard`.

Requires Python 3.10 or later. The only runtime dependency is [`cryptography`](https://cryptography.io).

## Documentation

- [Get started](https://github.com/xeroxzen/oppwa-guard/blob/main/docs/get-started.md): verify your first payment in five minutes.
- Concepts
  - [Threat model](https://github.com/xeroxzen/oppwa-guard/blob/main/docs/concepts/threat-model.md): the four failures and why each one happens.
- How-to guides
  - [Verify a shopper return](https://github.com/xeroxzen/oppwa-guard/blob/main/docs/how-to/verify-shopper-return.md)
  - [Handle webhook notifications](https://github.com/xeroxzen/oppwa-guard/blob/main/docs/how-to/handle-webhooks.md)
  - [Credit each payment exactly once](https://github.com/xeroxzen/oppwa-guard/blob/main/docs/how-to/credit-exactly-once.md)
  - [Test your integration](https://github.com/xeroxzen/oppwa-guard/blob/main/docs/how-to/test-your-integration.md)
- Reference
  - [Python API](https://github.com/xeroxzen/oppwa-guard/blob/main/docs/reference/api.md)
  - [Result codes](https://github.com/xeroxzen/oppwa-guard/blob/main/docs/reference/result-codes.md)
- [Troubleshooting](https://github.com/xeroxzen/oppwa-guard/blob/main/docs/troubleshooting.md)
- [Changelog](https://github.com/xeroxzen/oppwa-guard/blob/main/CHANGELOG.md)

## Scope

- oppwa-guard makes no HTTP calls. You keep your own client, timeouts and retries.
- Result-code patterns follow the public OPPWA result-code reference. Some acquirers add their own codes, so check yours.
- It reduces risk; it isn't a certification. Have your integration reviewed.

## Contributing and security

See [CONTRIBUTING.md](https://github.com/xeroxzen/oppwa-guard/blob/main/CONTRIBUTING.md). To report a vulnerability, follow [SECURITY.md](https://github.com/xeroxzen/oppwa-guard/blob/main/SECURITY.md) instead of opening a public issue.

## License

[MIT](https://github.com/xeroxzen/oppwa-guard/blob/main/LICENSE)
