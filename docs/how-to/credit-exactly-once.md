# Credit each payment exactly once

The same payment reaches you more than once in normal operation: gateway retries, the shopper return arriving alongside the webhook, and replays. This guide shows you how to make the database guarantee that each payment is credited only once.

## How it works

`claim_payment` inserts the payment id into a table whose primary key is that id. The database allows exactly one insert per id, no matter how many workers or servers try at once. The caller whose insert succeeds credits the order. Everyone else does nothing.

The claim must be in the **same transaction** as the credit. If the credit fails and rolls back, the claim rolls back with it, so a retry can succeed.

## SQLite

1. Create the table once, at startup or in a migration:

   ```python
   from oppwa_guard import ensure_schema

   ensure_schema(conn)
   ```

2. Claim and credit inside one transaction:

   ```python
   from oppwa_guard import claim_payment


   def fulfil_once(conn, order, payment_id):
       with conn:  # one transaction: commits on success, rolls back on exception
           if claim_payment(conn, payment_id):
               conn.execute(
                   "UPDATE orders SET status = 'paid', payment_id = ? WHERE id = ?",
                   (payment_id, order.id),
               )
   ```

## PostgreSQL

`claim_payment` takes a `sqlite3.Connection`. For PostgreSQL, run the equivalent statement yourself:

```sql
CREATE TABLE IF NOT EXISTS processed_payments (
    payment_id   TEXT PRIMARY KEY,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

```python
def fulfil_once(conn, order, payment_id):
    with conn.transaction():
        claimed = conn.execute(
            "INSERT INTO processed_payments (payment_id) VALUES (%s) "
            "ON CONFLICT (payment_id) DO NOTHING RETURNING payment_id",
            (payment_id,),
        ).fetchone()
        if claimed is not None:
            conn.execute(
                "UPDATE orders SET status = 'paid', payment_id = %s WHERE id = %s",
                (payment_id, order.id),
            )
```

This example uses [psycopg 3](https://www.psycopg.org/psycopg3/). A row back from `RETURNING` means this caller won the claim.

## Common mistakes

| Mistake | What goes wrong |
|---|---|
| Checking `SELECT ... WHERE payment_id = ?` first, then inserting | Two callers both see "not processed" before either writes |
| Using a `threading.Lock` or `asyncio.Lock` | Protects one process only |
| Claiming in one transaction and crediting in another | A crash between the two leaves a payment claimed but never credited |
| Using the order id as the key | A second, different payment for the same order is silently dropped. Key on the payment id. |

## Check that it works

The test suite runs `claim_payment` from 12 threads against the same id and asserts that exactly one wins. Do the same against your own database in your integration tests. See [Test your integration](test-your-integration.md).
