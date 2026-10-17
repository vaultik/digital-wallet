# TODO

## Known issues
- `get_or_create_wallet`: phantom read on concurrent first deposit in a new
  currency. Fix with IntegrityError retry inside `begin_nested()`, same
  pattern as `WebhookIdempotencyRepository.register_event`.
- Transaction boundaries are split across layers: `WalletService.transfer`
  commits the ledger, then the router commits the idempotency response.
  Two commits per operation. Move transaction control to the router (or a
  unit-of-work dependency) and drop `commit()` from the services, so the
  whole operation lands in one transaction.
- Idempotent replay goes back through `response_model`, so the stored body
  is re-parsed and re-serialized instead of being returned verbatim. Return
  the stored JSON directly, along with its stored status code.
- Idempotency records are never expired. Stripe keeps keys for 24h; decide
  on a retention window and clean up (Celery is already in the stack).
- `logout` hardcodes `secure=True` while `set_refresh_cookie` reads
  `environment`. Extract a matching `clear_refresh_cookie` helper.
- System user's `hashed_password` holds a dummy string instead of an
  explicit "login disabled" marker. Needs a data migration.
- Dependency factories are inconsistent: `WalletService` resolves via bare
  `Depends()`, others via explicit factories.
- `credit_external_deposit` returns None, so the caller cannot reference the
  operation it just performed. Return the `group_id` from
  `_lock_and_apply_double_entry` instead.

## Before Stage 1 (risk engine)
- Introduce a `Transfer` entity above ledger entries so risk score,
  decision and check status have somewhere to live.
- Rename `group_id` to `transfer_id` in the API response.

## Later
- Cache user lookups in `get_current_user` (Redis, short TTL) if the
  per-request DB hit shows up in profiling.
- Alerting on repeated failed logins — belongs to the risk engine.
