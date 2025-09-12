import os
import random
import string
import time
import hmac
import hashlib
from datetime import datetime
from urllib.parse import urlparse

from django.conf import settings
# Integration helpers may have additional dependencies (e.g., requests). For
# utility functions that don't need them, fall back to no-op implementations if
# the import fails so that status extraction tests can run without the extra
# packages installed.
try:  # pragma: no cover - exercised indirectly
    from .integrations.hdfc import _sanitize_order_id, _amount_str
except Exception:  # pragma: no cover
    def _sanitize_order_id(order_id: str) -> str:  # type: ignore
        return str(order_id)

    def _amount_str(amount) -> str:  # type: ignore
        return str(amount)

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


# --- Status normalization ---

SUCCESS_STATUSES = {"CHARGED", "SUCCESS", "SUCCESSFUL", "PAID", "CAPTURED", "COMPLETED", "SETTLED", "PROCESSED"}
PENDING_STATUSES = {"PENDING", "AUTHORIZED", "INITIATED", "IN_PROGRESS", "PROCESSING", "CREATED"}
FAILED_STATUSES  = {"FAILED", "DECLINED", "CANCELLED", "CANCELED", "VOID"}

# Optional fallbacks, can be toggled via env but our extractor will safely
# fall back to root/result only if nested fields are missing
ALLOW_ROOT_STATUS   = (os.getenv("HDFC_STATUS_FALLBACK_ROOT", "true").lower() in ("1","true","yes"))
ALLOW_RESULT_STATUS = (os.getenv("HDFC_STATUS_FALLBACK_RESULT", "true").lower() in ("1","true","yes"))

def extract_payment_status(payload: dict) -> tuple[str, str, str]:
    """Return (status, category, source).

    - status: normalized uppercase status string or ''
    - category: one of 'success' | 'pending' | 'failed' | 'unknown'
    - source: which field path provided the status
    """
    d = payload or {}
    # Try a prioritized list of nested paths
    paths = [
        ("order.status", ("order", "status")),
        ("order.state", ("order", "state")),
        ("order.current_status", ("order", "current_status")),
        ("order.order_status", ("order", "order_status")),
        ("result.order_status", ("result", "order_status")),
        ("payment.status", ("payment", "status")),
        ("payment.state", ("payment", "state")),
        ("payment.current_status", ("payment", "current_status")),
        ("payment.order_status", ("payment", "order_status")),
        ("transaction.status", ("transaction", "status")),
        ("transaction.state", ("transaction", "state")),
        ("transaction.order_status", ("transaction", "order_status")),
        ("txn_detail.status", ("txn_detail", "status")),
        ("txn_detail.order_status", ("txn_detail", "order_status")),
    ]
    status = ""; src = ""
    for label, (p1, p2) in paths:
        try:
            if isinstance(d.get(p1), dict) and d[p1].get(p2):
                s = str(d[p1].get(p2))
                status = s.upper(); src = label
                break
        except Exception:
            pass
    # payments array last item
    if not status and isinstance(d.get("payments"), list) and d["payments"]:
        try:
            s = str((d["payments"][-1] or {}).get("status", ""))
            if s:
                status = s.upper(); src = "payments[-1].status"
        except Exception:
            pass
    # Safe fallbacks: only if nothing found
    if not status and ALLOW_ROOT_STATUS and d.get("status"):
        s = str(d.get("status"));
        up = s.upper()
        if up in SUCCESS_STATUSES | PENDING_STATUSES | FAILED_STATUSES:
            status = up; src = "status"
    if not status and ALLOW_RESULT_STATUS and isinstance(d.get("result"), dict) and d["result"].get("status"):
        s = str(d["result"].get("status"))
        up = s.upper()
        if up in SUCCESS_STATUSES | PENDING_STATUSES | FAILED_STATUSES:
            status = up; src = "result.status"

    if status in SUCCESS_STATUSES:
        return status, "success", src
    if status in PENDING_STATUSES:
        return status, "pending", src
    if status in FAILED_STATUSES:
        return status, "failed", src
    return status, "unknown", src
