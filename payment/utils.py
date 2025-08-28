"""Utility helpers for the payment app."""

import hmac, hashlib, jwt, logging
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


logger = logging.getLogger(__name__)


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
    Build the HMAC string from the same fields (in order) that SmartGateway
    signed. You configure ``fields_in_mac`` from the doc/sample (common:
    ``order_id``, ``amount``, ``status``, ``merchant_id``).

    If ``settings.HDFC_SMART['RESPONSE_KEY']`` is missing, the function
    raises :class:`ImproperlyConfigured` and logs an error before computing
    the HMAC.
    """

    secret = settings.HDFC_SMART.get("RESPONSE_KEY")
    if not secret:
        logger.error("HDFC SmartGateway RESPONSE_KEY missing in settings")
        raise ImproperlyConfigured(
            "HDFC_SMART['RESPONSE_KEY'] setting is required to verify HMAC"
        )

    secret = secret.encode()
    msg = "|".join(
        "" if payload.get(k) is None else str(payload[k]) for k in fields_in_mac
    ).encode()
    expected = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, (received_sig or "").strip())


def verify_response_jwt(token: str):
    """Verify a JWT response from HDFC using the configured public key.

    The SmartGateway may return certain responses as a JWT signed with
    HDFC's private key.  We load the corresponding public key from
    ``settings.HDFC_SMART["PUBLIC_KEY_PATH"]`` and attempt to decode the
    token using RS256.  The decoded payload is returned on success; if the
    token cannot be verified ``None`` is returned.
    """

    key_path = settings.HDFC_SMART["PUBLIC_KEY_PATH"]
    with open(key_path) as fh:
        public_key = fh.read()

    try:
        return jwt.decode(token, public_key, algorithms=["RS256"])
    except jwt.PyJWTError:
        return None
