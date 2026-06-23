# Easebuzz Payment Gateway Integration (Django)

This guide aligns the Easebuzz integration to the current codebase and donation flow.

## 1) Prerequisites (already in this repo)

- `easebuzz_lib/` is present at the project root.
- A reusable wrapper is implemented at `payments/integrations/easebuzz.py`.

No external SDK install is required beyond the existing `easebuzz_lib`.

---

## 2) Environment configuration

Set these in `.env` (or your production environment):

```
PAYMENT_GATEWAY=EASEBUZZ
EASEBUZZ_MERCHANT_KEY=your_key
EASEBUZZ_SALT=your_salt
EASEBUZZ_ENV=test   # or prod
```

Notes:
- `PAYMENT_GATEWAY` controls which flow `donate_checkout` uses.
- Keep `EASEBUZZ_ENV=test` until real transactions are verified.

---

## 3) URLs you must expose

The donation flow posts to this response URL (used for both `surl` and `furl`):

```
https://<your-domain>/donations/donate/easebuzz/response
```

This endpoint is implemented in `donations/views.py` as `easebuzz_response` and is CSRF-exempt because the gateway posts server-to-server.

---

## 4) How the donation flow works (current code)

1. `donate_checkout` generates a `txn_id` and calls `easebuzz_create_payment`.
2. Easebuzz returns a payment link. We validate it with `allowed_payment_redirect`.
3. We save a `Donation` and mirror it into `payments.Order`.
4. The donor is redirected to the Easebuzz payment page.
5. Easebuzz posts back to `easebuzz_response`.
6. We verify hash via `easebuzz_verify_response`, update `Donation` and `Order`, and render `donations/thank_you.html`.

All of this is already wired in code. Ensure `PAYMENT_GATEWAY=EASEBUZZ` to activate it.

---

## 5) Required request fields (internal wrapper)

`payments/integrations/easebuzz.py` sends these fields:

- `txnid` (our internal `txn_id`)
- `firstname`
- `phone`
- `email`
- `amount`
- `productinfo`
- `surl`, `furl`
- `address1`, `address2`, `city`, `state`, `country`, `zipcode`
- `udf1`..`udf5` (used for internal metadata)

The wrapper already formats amount and sanitizes `txnid`.

---

## 6) Response verification and safety

- The response handler calls `easebuzz_verify_response` which validates the hash.
- For successful payments, it optionally calls the transaction lookup API to confirm.
- The response view is CSRF-exempt, but we still validate the hash.
- Redirect URLs are validated against allowed hosts in `payments/utils.py`.

Allowed Easebuzz hosts are currently:
- `pay.easebuzz.in`
- `testpay.easebuzz.in`
- `devpay.easebuzz.in`

---

## 7) Go-live checklist

1. Confirm the response URL is reachable over HTTPS.
2. Complete at least one test transaction with `EASEBUZZ_ENV=test`.
3. Switch to production keys and set `EASEBUZZ_ENV=prod`.
4. Verify `PAYMENT_GATEWAY=EASEBUZZ` is set in production.
5. Ensure emails/receipts are sent for successful payments.
6. Monitor failures and reconcile via transaction lookup if needed.

---

## 8) Optional local testing

If you want to experiment with Easebuzz’s sample kit:

1. Clone and run the Easebuzz Django kit locally.
2. Observe request/response behavior.
3. Compare with our wrapper in `payments/integrations/easebuzz.py`.
