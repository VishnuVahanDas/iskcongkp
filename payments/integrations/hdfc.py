# payments/integrations/hdfc.py
from dotenv import load_dotenv
load_dotenv()

import os
import re
import json
import base64
from decimal import Decimal, ROUND_HALF_UP
import requests

# ---- Configuration (env-driven) ----
HDFC_BASE_URL = os.getenv("HDFC_BASE_URL", "https://smartgatewayuat.hdfcbank.com")  # PROD by default
HDFC_API_KEY = os.getenv("HDFC_API_KEY", "")            # raw key from dashboard (NOT base64)
HDFC_MERCHANT_ID = os.getenv("HDFC_MERCHANT_ID", "")
HDFC_CLIENT_ID = os.getenv("HDFC_MERCHANT_ID", HDFC_MERCHANT_ID)
HDFC_RESELLER_ID = os.getenv("HDFC_RESELLER_ID", "hdfc_reseller")
HDFC_RETURN_URL = os.getenv("HDFC_RETURN_URL", "")
HDFC_APPEND_COLON = os.getenv("HDFC_APPEND_COLON", "False").lower() in ("1", "true", "yes")

# In PROD, client id must equal MID
HDFC_CLIENT_ID = HDFC_MERCHANT_ID

class HdfcError(Exception):
    pass

def _encode_api_key() -> str:
    if not HDFC_API_KEY:
        raise HdfcError("Missing HDFC_API_KEY")
    # Docs: Authorization = Basic base64(API_KEY)  (NO colon). Toggle only if bank requires.
    raw = HDFC_API_KEY + (":" if HDFC_APPEND_COLON else "")
    return base64.b64encode(raw.encode("utf-8")).decode("utf-8")

def _headers(customer_id: str) -> dict:
    return {
        "Authorization": f"Basic {_encode_api_key()}",
        "Content-Type": "application/json",
        "x-merchantid": HDFC_MERCHANT_ID,
        "x-customerid": customer_id,
        "x-resellerid": HDFC_RESELLER_ID,
    }

def _sanitize_order_id(order_id: str) -> str:
    # <21 chars, alphanumeric only
    clean = re.sub(r"[^A-Za-z0-9]", "", order_id or "")
    return clean[:20]

def _amount_str(amount) -> str:
    q = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s = format(q, "f")
    return s if (("." in s) and (not s.endswith(".00"))) else (s[:-3] if s.endswith(".00") else s)

def create_session(
    *,
    order_id: str,
    amount,
    customer_id: str,
    customer_email: str,
    customer_phone: str,
    first_name: str = "",
    last_name: str = "",
    description: str = "",
    currency: str = "INR",
) -> dict:
    if not HDFC_MERCHANT_ID:
        raise HdfcError("Missing HDFC_MERCHANT_ID")
    if not HDFC_RETURN_URL or not HDFC_RETURN_URL.startswith("https://") or "?" in HDFC_RETURN_URL:
        raise HdfcError("Invalid HDFC_RETURN_URL (must be HTTPS, no query params)")

    safe_order_id = _sanitize_order_id(order_id)
    payload = {
        "order_id": safe_order_id,
        "amount": _amount_str(amount),
        "customer_id": customer_id,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "payment_page_client_id": HDFC_CLIENT_ID,  # PROD requires MID
        "action": "paymentPage",
        "return_url": HDFC_RETURN_URL,
        "description": description or "Complete your payment",
        "first_name": first_name or "",
        "last_name": last_name or "",
        "currency": currency or "INR",
    }

    url = f"{HDFC_BASE_URL}/session"
    resp = requests.post(url, headers=_headers(customer_id), json=payload, timeout=30)

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    if resp.status_code == 200:
        return {"ok": True, "status_code": resp.status_code, "data": data}

    if resp.status_code == 401:
        hint = "Check Authorization header (Base64 of API key). Docs say no colon; use HDFC_APPEND_COLON=false."
    elif resp.status_code == 400:
        hint = "Bad request: order_id (<21 alnum), amount format, return_url (HTTPS, no query), payment_page_client_id=MID."
    elif resp.status_code in (404, 500):
        hint = f"Gateway error {resp.status_code}. Verify endpoint {url} and headers."
    else:
        hint = f"HTTP {resp.status_code}"

    raise HdfcError(f"Create session failed: {hint}. Response: {json.dumps(data)[:800]}")

def get_order_status(order_id: str, customer_id: str) -> dict:
    safe_order_id = _sanitize_order_id(order_id)
    url = f"{HDFC_BASE_URL}/orders/{safe_order_id}"
    resp = requests.get(url, headers=_headers(customer_id), timeout=30)

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    if resp.status_code == 200:
        return {"ok": True, "status_code": resp.status_code, "data": data}

    if resp.status_code == 401:
        hint = "Check Authorization header (Base64 of API key). Docs say no colon; use HDFC_APPEND_COLON=false."
    elif resp.status_code == 400:
        hint = "Bad request: order_id/customer_id/header values."
    elif resp.status_code in (404, 500):
        hint = f"Gateway error {resp.status_code}. Verify endpoint {url} and headers."
    else:
        hint = f"HTTP {resp.status_code}"

    raise HdfcError(f"Order status failed: {hint}. Response: {json.dumps(data)[:800]}")
