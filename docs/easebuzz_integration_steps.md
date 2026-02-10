# Easebuzz Payment Gateway Integration (Implemented in this project)

This repository now includes Easebuzz integration endpoints under the `payments` app.

## 1) Add Easebuzz SDK library

Copy `easebuzz_lib/` to the project root (same folder level as `manage.py`), as provided in Easebuzz's Django kit.

Expected import used by code:

```python
from easebuzz_lib.easebuzz_payment_gateway import Easebuzz
```

> If this folder is not present, the new API endpoints will return a clear error that `easebuzz_lib` is missing.

## 2) Configure environment variables

Set these in your `.env`:

```ini
EASEBUZZ_MERCHANT_KEY=your_merchant_key
EASEBUZZ_SALT=your_salt
EASEBUZZ_ENV=test
```

- Use `test` for UAT
- Switch to `prod` only after UAT sign-off

## 3) Start Django server

```bash
python manage.py runserver
```

## 4) Initiate payment from your frontend/backend client

Endpoint:

- `POST /payments/easebuzz/initiate`

Required JSON fields:

- `firstname`
- `phone`
- `email`
- `amount`
- `productinfo`

Optional:

- `txnid` (auto-generated if omitted)
- `surl`, `furl` (defaults to `/payments/easebuzz/response`)
- `city`, `zipcode`, `address1`, `address2`, `state`, `country`, `udf1..udf5`

Example payload:

```json
{
  "firstname": "Jitendra",
  "phone": "9999999999",
  "email": "jitendra@example.com",
  "amount": "1.03",
  "productinfo": "Apple Mobile"
}
```

Success response includes `payment_url` for redirect:

```json
{
  "ok": true,
  "txnid": "EZB...",
  "payment_url": "https://..."
}
```

## 5) Handle Easebuzz gateway callback

Endpoint already added:

- `POST /payments/easebuzz/response`

Set this URL in Easebuzz (`surl`/`furl`) or pass custom callback URLs while initiating payment.

The endpoint parses posted form data through Easebuzz SDK response helper and returns JSON.

## 6) Production checklist

1. Keep `EASEBUZZ_ENV=test` until all cases pass.
2. Ensure callback URLs are HTTPS and publicly reachable.
3. Move to `EASEBUZZ_ENV=prod` with production key/salt.
4. Persist payment outcomes in your business models before fulfillment.
5. Add reconciliation jobs (transaction/refund APIs) if required by your ops flow.
