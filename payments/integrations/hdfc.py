from dotenv import load_dotenv
load_dotenv()

import os, re, json, base64
from decimal import Decimal, ROUND_HALF_UP
import requests
from requests import RequestException

HDFC_BASE_URL    = os.getenv("HDFC_BASE_URL", "https://smartgateway.hdfcbank.com")
HDFC_API_KEY     = os.getenv("HDFC_API_KEY", "")
HDFC_MERCHANT_ID = os.getenv("HDFC_MERCHANT_ID", "")
HDFC_RESELLER_ID = os.getenv("HDFC_RESELLER_ID", "hdfc_reseller")
HDFC_RETURN_URL  = os.getenv("HDFC_RETURN_URL", "")
HDFC_APPEND_COLON = os.getenv("HDFC_APPEND_COLON", "false").lower() in ("1", "true", "yes")
# UAT override: set HDFC_CLIENT_ID=hdfcmaster in .env; PROD: omit -> defaults to MID
HDFC_CLIENT_ID   = os.getenv("HDFC_CLIENT_ID", HDFC_MERCHANT_ID)

class HdfcError(Exception): pass

def _encode_api_key() -> str:
    if not HDFC_API_KEY: raise HdfcError("Missing HDFC_API_KEY")
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
    return (re.sub(r"[^A-Za-z0-9]", "", order_id or ""))[:20]  # <21 alnum

def _amount_str(amount) -> str:
    try:
        q = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        s = format(q, "f")
        return s if (("." in s) and (not s.endswith(".00"))) else (s[:-3] if s.endswith(".00") else s)
    except Exception:
        raise HdfcError("Invalid amount value")

def create_session(*, order_id, amount, customer_id, customer_email, customer_phone,
                   first_name="", last_name="", description="", currency="INR") -> dict:
    if not HDFC_MERCHANT_ID: raise HdfcError("Missing HDFC_MERCHANT_ID")
    if not HDFC_RETURN_URL or not HDFC_RETURN_URL.startswith("https://") or "?" in HDFC_RETURN_URL:
        raise HdfcError("Invalid HDFC_RETURN_URL (must be HTTPS, no query params)")
    payload = {
        "order_id": _sanitize_order_id(order_id),
        "amount": _amount_str(amount),
        "customer_id": customer_id,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "payment_page_client_id": HDFC_CLIENT_ID,
        "action": "paymentPage",
        "return_url": HDFC_RETURN_URL,
        "description": description or "Complete your payment",
        "first_name": first_name or "",
        "last_name": last_name or "",
        "currency": currency or "INR",
    }
    url = f"{HDFC_BASE_URL}/session"
    try:
        resp = requests.post(url, headers=_headers(customer_id), json=payload, timeout=30)
    except RequestException as e:
        raise HdfcError(f"Gateway request failed: {e}")
    try: data = resp.json()
    except Exception: data = {"raw": resp.text}
    if resp.status_code == 200: return {"ok": True, "status_code": 200, "data": data}
    if resp.status_code == 401: hint="Check Authorization (Basic base64(API_KEY)). Toggle APPEND_COLON only if bank requires."
    elif resp.status_code == 400: hint="Bad request: order_id/amount/return_url/client_id."
    elif resp.status_code in (404,500): hint=f"Gateway error {resp.status_code}."
    else: hint=f"HTTP {resp.status_code}"
    raise HdfcError(f"Create session failed: {hint}. Response: {json.dumps(data)[:800]}")

def get_order_status(order_id: str, customer_id: str) -> dict:
    url = f"{HDFC_BASE_URL}/orders/{_sanitize_order_id(order_id)}"
    try:
        resp = requests.get(url, headers=_headers(customer_id), timeout=30)
    except RequestException as e:
        raise HdfcError(f"Gateway request failed: {e}")
    try: data = resp.json()
    except Exception: data = {"raw": resp.text}
    if resp.status_code == 200: return {"ok": True, "status_code": 200, "data": data}
    if resp.status_code == 401: hint="Check Authorization."
    elif resp.status_code == 400: hint="Bad request: order_id/customer_id/headers."
    elif resp.status_code in (404,500): hint=f"Gateway error {resp.status_code}."
    else: hint=f"HTTP {resp.status_code}"
    raise HdfcError(f"Order status failed: {hint}. Response: {json.dumps(data)[:800]}")
