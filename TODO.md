# TODO

## Known issues
- `get_or_create_wallet`: phantom read on concurrent first deposit in a new
  currency. Fix with IntegrityError retry inside `begin_nested()`, same
  pattern as `WebhookIdempotencyRepository.register_event`.
- `logout` hardcodes `secure=True` while `set_refresh_cookie` reads
  `environment`. Extract a matching `clear_refresh_cookie` helper.
- System user's `hashed_password` holds a dummy string instead of an
  explicit "login disabled" marker. Needs a data migration.
- Dependency factories are inconsistent: `WalletService` resolves via bare
  `Depends()`, others via explicit factories.

## Before Stage 1 (risk engine)
- Introduce a `Transfer` entity above ledger entries so risk score,
  decision and check status have somewhere to live.
- Rename `group_id` to `transfer_id` in the API response.

## Later
- Cache user lookups in `get_current_user` (Redis, short TTL) if the
  per-request DB hit shows up in profiling.
- Alerting on repeated failed logins — belongs to the risk engine.
