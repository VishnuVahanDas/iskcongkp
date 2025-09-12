import random
import string
from datetime import datetime
from urllib.parse import urlparse

from django.conf import settings

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
