import os
import re
import random
import string
from datetime import datetime
from urllib.parse import urlparse


ALNUM = string.ascii_uppercase + string.digits


def _sanitize_order_id(order_id: str) -> str:
    """Strip non-alphanumeric chars and truncate to 20 chars (gateway requirement)."""
    return (re.sub(r"[^A-Za-z0-9]", "", order_id or ""))[:20]


def generate_order_id(prefix="ORD"):
    ts = datetime.utcnow().strftime("%m%d%H%M%S")  # 10 chars
    rand = "".join(random.choices(ALNUM, k=6))
    base = f"{prefix}{ts}{rand}"  # may be >20
    # Return last 20 alnum chars (bank requires <21)
    return base[-20:]


def allowed_payment_redirect(url: str) -> bool:
    """Validate gateway redirect URLs to prevent open redirects.

    Only allow HTTPS URLs to known payment gateway hosts.
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
    allowed_hosts = {
        "pay.easebuzz.in",
        "testpay.easebuzz.in",
        "devpay.easebuzz.in",
        "links.juspay.in",
        "api.juspay.in",
    }
    if host in allowed_hosts:
        return True
    if host.endswith(".juspay.in"):
        return True
    return False


# --- Status normalization ---

SUCCESS_STATUSES = {"CHARGED", "SUCCESS", "SUCCESSFUL", "PAID", "CAPTURED", "COMPLETED", "SETTLED", "PROCESSED"}
PENDING_STATUSES = {"PENDING", "AUTHORIZED", "INITIATED", "IN_PROGRESS", "PROCESSING", "CREATED"}
FAILED_STATUSES  = {"FAILED", "DECLINED", "CANCELLED", "CANCELED", "VOID"}


def extract_payment_status(payload: dict) -> tuple[str, str, str]:
    """Return (status, category, source).

    - status: normalized uppercase status string or ''
    - category: one of 'success' | 'pending' | 'failed' | 'unknown'
    - source: which field path provided the status
    """
    d = payload or {}
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
    # Safe fallbacks
    if not status and d.get("status"):
        s = str(d.get("status"))
        up = s.upper()
        if up in SUCCESS_STATUSES | PENDING_STATUSES | FAILED_STATUSES:
            status = up; src = "status"
    if not status and isinstance(d.get("result"), dict) and d["result"].get("status"):
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
