# Easebuzz Payment Gateway Integration (Django)

This guide converts the raw integration kit notes into a clean, implementation-ready checklist for this Django project.

## 1) Run the Easebuzz integration kit locally (optional but recommended)

Use this once to understand request/response behavior before wiring it in your project.

### With virtual environment
1. Clone and unzip `paywitheasebuzz-python-django-lib`.
2. Activate your Python virtualenv:
   ```bash
   source bin/activate
   ```
3. Move to the kit folder.
4. Start server:
   ```bash
   python manage.py runserver
   ```
5. Open: `http://127.0.0.1:8000/`

### Without virtual environment
1. Move to the kit folder.
2. Run:
   ```bash
   python manage.py runserver
   ```
3. Open: `http://127.0.0.1:8000/`

---

## 2) Add Easebuzz library into your project

1. Copy `easebuzz_lib/` into your Django project root (same level as `manage.py`).
2. In the target view module, import:
   ```python
   from easebuzz_lib.easebuzz_payment_gateway import Easebuzz
   ```

---

## 3) Configure credentials safely

Set these values from environment variables (recommended), not hardcoded literals.

```python
import os

MERCHANT_KEY = os.getenv("EASEBUZZ_MERCHANT_KEY", "")
SALT = os.getenv("EASEBUZZ_SALT", "")
ENV = os.getenv("EASEBUZZ_ENV", "test")  # "test" or "prod"
```

Then create client object:

```python
easebuzz_obj = Easebuzz(MERCHANT_KEY, SALT, ENV)
```

---

## 4) Implement payment initiation endpoint

Use all required fields and generate a unique `txnid` per attempt.

```python
import json
from django.shortcuts import redirect, render

post_data = {
    "txnid": "UNIQUE_TXN_ID",
    "firstname": "Customer Name",
    "phone": "9999999999",
    "email": "customer@example.com",
    "amount": "1.03",
    "productinfo": "Order #123",
    "surl": "https://your-domain.com/payment/response/",
    "furl": "https://your-domain.com/payment/response/",
    "city": "City",
    "zipcode": "123456",
    "address2": "Address line 2",
    "state": "State",
    "address1": "Address line 1",
    "country": "India",
    "udf1": "meta1",
    "udf2": "meta2",
    "udf3": "meta3",
    "udf4": "meta4",
    "udf5": "meta5",
}

final_response = easebuzz_obj.initiatePaymentAPI(post_data)
result = json.loads(final_response)
if result.get("status") == 1:
    return redirect(result["data"])  # Payment link
return render(request, "response.html", {"response_data": final_response})
```

---

## 5) Implement callback/response handler

Easebuzz posts response data to `surl`/`furl` via HTTP form POST.

```python
final_response = easebuzz_obj.easebuzzResponse(request.POST)
return render(request, "response.html", {"response_data": final_response})
```

Validate status and store transaction result in your DB.

---

## 6) Optional operational APIs

### Transaction lookup
```python
post_data = {
    "txnid": "T300",
    "amount": "1.03",
    "phone": "1231231235",
    "email": "jitendra@gmail.com",
}
final_response = easebuzz_obj.transactionAPI(post_data)
```

### Transaction by date
```python
post_data = {
    "merchant_email": "jitendra@gmail.com",
    "transaction_date": "06-06-2018",
}
final_response = easebuzz_obj.transactionDateAPI(post_data)
```

### Refund
```python
post_data = {
    "txnid": "T300",
    "refund_amount": "0.9",
    "phone": "1231231235",
    "amount": "1.03",
    "email": "jitendra@gmail.com",
}
final_response = easebuzz_obj.refundAPI(post_data)
```

### Payout
```python
post_data = {
    "merchant_email": "jitendra@gmail.com",
    "payout_date": "06-06-2018",
}
final_response = easebuzz_obj.payoutAPI(post_data)
```

---

## 7) Go-live checklist

1. Keep `ENV=test` until test transactions are verified.
2. Confirm callback URLs are publicly reachable over HTTPS.
3. Move to production by setting `EASEBUZZ_ENV=prod` with production credentials.
4. Log request/response IDs (never log full secrets).
5. Ensure idempotency: same `txnid` should not create duplicate orders.
6. Add server-side verification before marking order as paid.
