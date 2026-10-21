# Digital Wallet

A multi-currency wallet API with strict double-entry bookkeeping, built to get the money parts right: exact decimal arithmetic, row-level locking against concurrent spends, and idempotent operations at both the client and webhook layer.

## Features
- Multi-currency wallets (USD, EUR, BTC)
- P2P transfers with idempotency keys
- Stripe deposits with webhook signature verification
- JWT auth with refresh token rotation

## Stack
Python 3.12, FastAPI, PostgreSQL, SQLAlchemy 2.0 (async), Alembic,
Redis, Stripe, pytest.

## Architecture

### Double-entry bookkeeping

A balance is never just a number that gets incremented. Every movement of
money writes two ledger rows sharing a `group_id`: a DEBIT on the source
wallet and a CREDIT on the destination. The `amount` is always positive —
direction is carried by `entry_type`, not by sign, so summing entries can
never accidentally cancel a debit against a credit.

This makes imbalance structurally impossible rather than something to guard
against: a wallet's balance must equal the sum of its entries, and a missing
counterpart is visible immediately.

### Concurrency

Concurrent spends are serialized by the database itself: wallet rows are
read with `SELECT ... FOR UPDATE`, so a second transaction touching the same
wallet waits instead of reading a stale balance. Without it two simultaneous
transfers would both read 1000, both decide the funds are sufficient, and the
second would overwrite the first — a lost update, and a way to spend money
twice.

Rows are always locked in a fixed order (`ORDER BY id`), so two transfers
involving the same pair of wallets can never deadlock by grabbing them in
opposite order.

### Idempotency

Two separate mechanisms, because retries come from two different places.

Transfers carry a client-supplied `Idempotency-Key`. The key is claimed
before the operation runs, so the unique constraint on `(user_id, key)`
serializes concurrent requests with the same key; a retry replays the stored
response instead of moving money again. The request body is hashed and stored
alongside, so reusing a key with different parameters is rejected rather than
silently answered with the old result.

Stripe webhooks use the provider's `event.id` instead — Stripe re-delivers
events on timeout, and a duplicate delivery must not credit the wallet twice.

The idempotency key and the operation's `group_id` answer different
questions: the key identifies an *attempt* and lives for hours, while the
`group_id` identifies the *operation* that happened and stays in the ledger
forever.

### System clearing wallet

External money has to come from somewhere, or double-entry breaks. Stripe
deposits debit a dedicated system clearing wallet and credit the user's,
which keeps every movement balanced. That wallet legitimately runs negative —
it represents money owed from outside the system — so the balance
`CheckConstraint` allows negative values for `is_system` wallets only.

### Decimal

All monetary values are `Decimal`, never `float`. Floats cannot represent
most decimal fractions exactly, so repeated arithmetic drifts: 0.1 + 0.2 is
not 0.3. Over thousands of transactions that drift becomes a real
discrepancy in the ledger.

### Transaction boundaries

One commit per top-level operation. Repositories only `flush()` and never
commit, so a failure anywhere in the chain rolls the whole thing back — a
transfer cannot leave a debit without its credit, and a deposit cannot credit
a wallet without recording that the webhook was processed.

## Run

Requires Python 3.12 and Docker.

    git clone https://github.com/vaultik/digital_wallet
    cd digital_wallet
    cp .env.example .env          # fill in SECRET and Stripe keys

    docker compose up -d          # PostgreSQL
    poetry install
    poetry run alembic upgrade head
    poetry run uvicorn app.main:app --reload

API docs: http://localhost:8000/docs

## Tests

    pytest

52 tests against a real PostgreSQL instance (no SQLite — the suite relies on
`SELECT FOR UPDATE`, CHECK constraints and SAVEPOINTs). Each test runs inside
a transaction that is rolled back on teardown, so the schema is migrated once
per session and seed data survives untouched.

## Structure

    app/
      api/            FastAPI routers and dependency wiring
      core/           config, security, exception handlers, idempotency guard
      models/         SQLAlchemy models (User, Wallet, Currency, Transaction)
      repositories/   data access; these flush, never commit
      schemas/        Pydantic request/response models
      services/       business logic (transfers, deposits, auth)
      tasks/          Celery tasks
      workers/        Celery worker entrypoints
    alembic/
      versions/       migrations, including currency and system user seeds
    docker/           container init scripts
    tests/
      unit/           no database
      integration/    real PostgreSQL, transactional rollback per test

## Roadmap
- Transaction history with pagination and filters
- Currency conversion
- Rule-based risk engine for transfers
- LLM layer explaining risk decisions
