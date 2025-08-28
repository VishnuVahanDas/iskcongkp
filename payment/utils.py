"""Utility helpers for the payment app."""

import hmac, hashlib, jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings


def jwt_auth_header() -> str:
    """Return the Bearer Authorization header for HDFC SmartGateway.

    The SmartGateway expects a JWT signed with the merchant's private
    key.  We read the private key from ``settings.HDFC_SMART["PRIVATE_KEY_PATH"]``
    and sign a payload containing ``KEY_UUID`` and ``PAYMENT_PAGE_CLIENT_ID``
    using the RS256 algorithm.  The resulting token is returned as a
    ``Bearer`` header value.
    """

    key_path = settings.HDFC_SMART["PRIVATE_KEY_PATH"]
    with open(key_path) as fh:
        private_key = fh.read()

    now = datetime.now(timezone.utc)
    payload = {
        "iss": settings.HDFC_SMART["PAYMENT_PAGE_CLIENT_ID"],
        "aud": settings.HDFC_SMART["BASE_URL"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "key_uuid": settings.HDFC_SMART["KEY_UUID"],
        "payment_page_client_id": settings.HDFC_SMART["PAYMENT_PAGE_CLIENT_ID"],
    }
    token = jwt.encode(payload, private_key, algorithm="RS256")
    return "Bearer " + token

def verify_hmac(payload: dict, received_sig: str, fields_in_mac: list) -> bool:
    """
    Build the HMAC string from the same fields (in order) that SmartGateway signed.
    You configure fields_in_mac from the doc/sample (common: order_id, amount, status, merchant_id).
    """
    secret = (settings.HDFC_SMART["RESPONSE_KEY"] or "").encode()
    msg = "|".join("" if payload.get(k) is None else str(payload[k]) for k in fields_in_mac).encode()
    expected = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, (received_sig or "").strip())
