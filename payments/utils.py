import os
import random
import string
import time
import hmac
import hashlib
from datetime import datetime
from urllib.parse import urlparse

from django.conf import settings
from .integrations.hdfc import _sanitize_order_id, _amount_str

ALNUM = string.ascii_uppercase + string.digits

def generate_order_id(prefix="ORD"):
    ts = datetime.utcnow().strftime("%m%d%H%M%S")  # 10 chars
    rand = "".join(random.choices(ALNUM, k=6))
    base = f"{prefix}{ts}{rand}"  # may be >20
    # Return last 20 alnum chars (bank requires <21)
    return base[-20:]

def allowed_payment_redirect(url: str) -> bool:
    """Validate gateway redirect URLs to prevent open redirects.

    Only allow HTTPS URLs to known HDFC/Juspay hosts.
    """
    try:
        p = urlparse(url)
    except Exception:
        return False
    if p.scheme.lower() != "https":
        return False
    host = (p.hostname or "").lower()
    if not host:
        return False
    # Allow HDFC SmartGateway UAT/PROD and common Juspay link hosts
    allowed_hosts = {
        "smartgateway.hdfcbank.com",
        "smartgatewayuat.hdfcbank.com",
        "links.juspay.in",
        "api.juspay.in",
    }
    if host in allowed_hosts:
        return True
    # Allow any subdomain of juspay.in (if bank routes via a different subdomain)
    if host.endswith(".juspay.in"):
        return True
    return False


# --- Request signing (tamper prevention for client-initiated create-session) ---

def _signing_secret() -> bytes:
    key = getattr(settings, "HDFC_REQUEST_SECRET", None) or os.getenv("HDFC_REQUEST_SECRET")
    if not key:
        # Fall back to SECRET_KEY in dev; set HDFC_REQUEST_SECRET in prod
        key = getattr(settings, "SECRET_KEY", "dev-secret")
    return key.encode("utf-8")

def _canonical_fields(payload: dict) -> tuple[str, ...]:
    oid = _sanitize_order_id(str(payload.get("order_id", "")))
    amt = _amount_str(payload.get("amount", "0"))
    currency = (payload.get("currency") or "INR").upper()
    cid = str(payload.get("customer_id", ""))
    email = str(payload.get("customer_email", ""))
    phone = str(payload.get("customer_phone", ""))
    desc = str(payload.get("description", ""))
    return (oid, amt, currency, cid, email, phone, desc)

def sign_session(payload: dict, ts: int | None = None) -> tuple[str, int]:
    ts = ts or int(time.time())
    parts = _canonical_fields(payload)
    data = "|".join(parts + (str(ts),))
    mac = hmac.new(_signing_secret(), data.encode("utf-8"), hashlib.sha256).hexdigest()
    return mac, ts

def verify_session_signature(payload: dict, sig_hex: str, ts: int, ttl_seconds: int = 600) -> bool:
    try:
        ts = int(ts)
    except Exception:
        return False
    now = int(time.time())
    if ts < (now - ttl_seconds) or ts > (now + 60):  # allow clock skew
        return False
    expected, _ = sign_session(payload, ts)
    try:
        return hmac.compare_digest(expected, str(sig_hex))
    except Exception:
        return False

def track_id_for(order_id: str, ts: int) -> str:
    base = f"{_sanitize_order_id(order_id)}|{int(ts)}".encode("utf-8")
    return hashlib.sha256(base).hexdigest()[:32]
