# Python API reference

Everything below is importable from `oppwa_guard` unless stated otherwise.

| Name | Kind | Purpose |
|---|---|---|
| [`verify_payment`](#verify_payment) | function | Decide whether a response pays for an order |
| [`ExpectedPayment`](#expectedpayment) | dataclass | What your database says the customer owes |
| [`Verdict`](#verdict) | dataclass | Result of `verify_payment` |
| [`Rejection`](#rejection) | enum | Why a payment was rejected |
| [`classify`](#classify) | function | Map a result code to an outcome |
| [`Outcome`](#outcome) | enum | Result-code categories |
| [`status_path`](#status_path) | function | Build the status path from a stored checkout id |
| [`resource_path_matches`](#resource_path_matches) | function | Detect an edited `resourcePath` |
| [`decrypt_notification`](#decrypt_notification) | function | Authenticate and decrypt a webhook |
| [`payment_payload`](#payment_payload) | function | Extract the payment from a notification |
| [`NotificationError`](#notificationerror) | exception | A notification failed authentication or parsing |
| [`claim_payment`](#claim_payment) | function | Claim a payment id exactly once |
| [`ensure_schema`](#ensure_schema) | function | Create the claims table in SQLite |

---

## Verification

### `verify_payment`

```python
verify_payment(
    expected: ExpectedPayment,
    response: Mapping[str, object],
    *,
    allow_test_mode: bool = False,
) -> Verdict
```

Decides whether `response` pays for `expected`. Fulfil the order only when `Verdict.accepted` is `True`.

| Parameter | Description |
|---|---|
| `expected` | The order as your database records it. |
| `response` | A payment-status body, or the `payload` of a decrypted notification. |
| `allow_test_mode` | Accept integrator test-mode codes (`000.100.1xx`). Use only against a test entity. |

Checks run in this order, and the first failure is returned:

1. `id` and `result.code` are present strings, otherwise `MALFORMED`.
2. The code is well formed, otherwise `MALFORMED`.
3. The code [classifies](#classify) as success, otherwise `TEST_MODE`, `NEEDS_REVIEW`, `PENDING` or `NOT_SUCCESSFUL`.
4. `merchantTransactionId` equals `expected.merchant_transaction_id`, otherwise `ORDER_MISMATCH`.
5. `paymentType` equals `expected.payment_type`, otherwise `PAYMENT_TYPE_MISMATCH`.
6. `currency` equals `expected.currency`, otherwise `CURRENCY_MISMATCH`.
7. `amount` parses as a decimal, otherwise `MALFORMED`.
8. `amount` equals `expected.amount`, otherwise `AMOUNT_MISMATCH`. `"250"` and `"250.00"` are equal.

**Raises:** nothing. Every problem with `response` is reported in the verdict.

### `ExpectedPayment`

```python
@dataclass(frozen=True)
class ExpectedPayment:
    merchant_transaction_id: str
    amount: Decimal
    currency: str
    payment_type: str = "DB"
```

| Field | Description |
|---|---|
| `merchant_transaction_id` | The value you sent as `merchantTransactionId` when creating the checkout. |
| `amount` | Amount owed. Positive, at most two decimal places. |
| `currency` | ISO 4217 code, three capital letters. |
| `payment_type` | OPPWA payment type. `DB` is a debit; use `PA` for a pre-authorisation. |

**Raises:** `ValueError` when constructed with an empty `merchant_transaction_id`, a malformed currency, or an amount that isn't positive with at most two decimals.

### `Verdict`

```python
@dataclass(frozen=True)
class Verdict:
    accepted: bool
    reason: Rejection | None
    detail: str
    payment_id: str | None
```

| Field | Description |
|---|---|
| `accepted` | `True` only when every check passed. |
| `reason` | `None` when accepted, otherwise the first failed check. |
| `detail` | A human-readable explanation for logs. Don't parse it. |
| `payment_id` | The response's `id`, when present. Pass it to `claim_payment`. |

### `Rejection`

| Member | Value | Meaning | Usual action |
|---|---|---|---|
| `MALFORMED` | `malformed_response` | Missing fields, bad code or unparseable amount | Don't fulfil; investigate |
| `NOT_SUCCESSFUL` | `not_successful` | Declined, rejected or errored | Don't fulfil |
| `PENDING` | `pending` | Not final yet | Wait for the webhook, or poll later |
| `NEEDS_REVIEW` | `needs_manual_review` | Succeeded but flagged for review | Hold the goods and review |
| `TEST_MODE` | `test_mode_result_in_live_check` | Integrator test-mode code | Treat as a configuration alarm |
| `ORDER_MISMATCH` | `merchant_transaction_id_mismatch` | Payment belongs to another order | Don't fulfil; log as a security event |
| `PAYMENT_TYPE_MISMATCH` | `payment_type_mismatch` | For example `PA` when you expected `DB` | Don't fulfil |
| `CURRENCY_MISMATCH` | `currency_mismatch` | Paid in a different currency | Don't fulfil; log as a security event |
| `AMOUNT_MISMATCH` | `amount_mismatch` | Paid a different amount | Don't fulfil; log as a security event |

---

## Result codes

### `classify`

```python
classify(code: str) -> Outcome
```

Maps an OPPWA `result.code` to an [`Outcome`](#outcome). See [Result codes](result-codes.md) for the patterns.

**Raises:** `ValueError` if `code` isn't of the form `ddd.ddd.ddd`.

### `Outcome`

| Member | Meaning |
|---|---|
| `SUCCESS` | Processed successfully |
| `TEST_MODE_SUCCESS` | Successful, but in integrator test mode |
| `SUCCESS_NEEDS_REVIEW` | Successful, flagged for manual review |
| `PENDING` | Not final |
| `REJECTED` | Anything else |

---

## Shopper return

### `status_path`

```python
status_path(stored_checkout_id: str) -> str
```

Returns `/v1/checkouts/{stored_checkout_id}/payment`. Pass the checkout id from your own database, never one from the browser.

**Raises:** `ValueError` unless the id is 1 to 128 characters of `A-Z`, `a-z`, `0-9`, `.` and `-`.

### `resource_path_matches`

```python
resource_path_matches(resource_path: str, stored_checkout_id: str) -> bool
```

Returns `True` when the browser's `resourcePath` is exactly the status path for the stored checkout. Use it to log tampering, not to decide what to fetch.

**Raises:** `ValueError` under the same condition as `status_path`.

---

## Webhooks

### `decrypt_notification`

```python
decrypt_notification(
    key: str,
    iv: str,
    tag: str,
    body: str | bytes,
    *,
    encoding: Literal["hex", "base64"] = "hex",
) -> dict[str, object]
```

Authenticates and decrypts an AES-256-GCM notification.

| Parameter | Description |
|---|---|
| `key` | The webhook secret, 256 bits, in `encoding`. |
| `iv` | The `X-Initialization-Vector` header. |
| `tag` | The `X-Authentication-Tag` header. |
| `body` | The raw request body. |
| `encoding` | How the key, IV, tag and body are encoded. |

**Raises:**

- `NotificationError` for anything wrong with `iv`, `tag` or `body`: bad encoding, wrong IV or tag length, failed authentication, or a plaintext that isn't a JSON object. All of these come from the request, so respond `400`.
- `ValueError` if `key` isn't 256 bits. This is a configuration error on your side.

### `payment_payload`

```python
payment_payload(notification: Mapping[str, object]) -> Mapping[str, object]
```

Returns the `payload` object of a notification whose `type` is `PAYMENT`.

**Raises:** `NotificationError` for any other `type`, or when `payload` isn't an object.

### `NotificationError`

Subclass of `Exception`. The notification couldn't be authenticated or parsed. Respond with a non-2xx status and change nothing.

### `encrypt_notification_for_testing`

```python
from oppwa_guard.webhook import encrypt_notification_for_testing

encrypt_notification_for_testing(key_hex: str, notification: Mapping[str, object]) -> dict[str, str]
```

Returns `{"body", "iv", "tag"}` in hex, as OPPWA would send them. For tests and local simulators only. See [Test your integration](../how-to/test-your-integration.md).

---

## Idempotency

### `claim_payment`

```python
claim_payment(conn: sqlite3.Connection, payment_id: str) -> bool
```

Inserts `payment_id` into `processed_payments`. Returns `True` for exactly one caller per id and `False` for every other caller. Call it inside the transaction that credits the order. See [Credit each payment exactly once](../how-to/credit-exactly-once.md).

**Raises:** `ValueError` if `payment_id` is empty. `sqlite3` errors propagate.

### `ensure_schema`

```python
ensure_schema(conn: sqlite3.Connection) -> None
```

Creates the `processed_payments` table if it doesn't exist. The statement is also available as `oppwa_guard.idempotency.SQLITE_SCHEMA`.
