# payments/services.py
import requests
from django.conf import settings

HDFC_BASE = getattr(settings, "HDFC_BASE_URL", "https://smartgateway.hdfcbank.com")

def create_session(*, txn_id, amount, donor, purpose, return_url, webhook_url):
    payload = {
        "order_id": txn_id,
        "amount": str(amount),
        "currency": "INR",
        "customer_id": donor.email or donor.phone_e164 or f"donor-{donor.id}",
        "customer_email": donor.email,
        "customer_phone": donor.phone_e164,
        "first_name": (donor.name or "Devotee").split(" ")[0],
        "last_name": " ",
        "description": purpose or "Donation",
        "return_url": return_url,   # browser comes here
        "webhook_url": webhook_url, # server notify
    }
    headers = {
        "Content-Type": "application/json",
        # adapt to your existing auth (JWT/API key/KID)
        "Authorization": f"Bearer {settings.HDFC_JWT}",
        "kid": getattr(settings, "HDFC_JWT_KID", ""),
    }
    r = requests.post(f"{HDFC_BASE}/session", json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    # Make sure your real response keys match these:
    return {"id": data["id"], "redirect_url": data["redirect_url"]}
