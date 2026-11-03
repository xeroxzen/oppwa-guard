# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-04

### Added

- `verify_payment`, `ExpectedPayment`, `Verdict` and `Rejection`: bind a payment to an order by reference, payment type, currency and amount.
- `classify` and `Outcome`: result-code classification with test mode kept separate from success.
- `status_path` and `resource_path_matches`: build the status request from the stored checkout id.
- `decrypt_notification` and `payment_payload`: AES-256-GCM webhook decryption, hex or Base64.
- `claim_payment` and `ensure_schema`: exactly-once crediting through a primary-key constraint.
- `oppwa_guard.webhook.encrypt_notification_for_testing` for tests.

[0.1.0]: https://github.com/xeroxzen/oppwa-guard/releases/tag/v0.1.0
