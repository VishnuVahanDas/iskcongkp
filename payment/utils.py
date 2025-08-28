# payment/utils.py
import base64, hmac, hashlib
from django.conf import settings

def basic_auth_header():
    """Return Authorization header for HDFC SmartGateway.

    The gateway expects a Basic auth header where the string
    ``<CLIENT_ID>:<API_KEY>`` (or ``<API_KEY>:`` if client ID is not
    required) is Base64 encoded.  Previously we encoded only the API key
    itself which resulted in an incorrect header when a client ID was
    needed.
    """

    api_key = settings.HDFC_SMART["API_KEY"] or ""
    client_id = settings.HDFC_SMART.get("CLIENT_ID")

    if client_id:
        token = f"{client_id}:{api_key}"
    else:
        token = f"{api_key}:"

    return "Basic " + base64.b64encode(token.encode()).decode()

def verify_hmac(payload: dict, received_sig: str, fields_in_mac: list) -> bool:
    """
    Build the HMAC string from the same fields (in order) that SmartGateway signed.
    You configure fields_in_mac from the doc/sample (common: order_id, amount, status, merchant_id).
    """
    secret = (settings.HDFC_SMART["RESPONSE_KEY"] or "").encode()
    msg = "|".join("" if payload.get(k) is None else str(payload[k]) for k in fields_in_mac).encode()
    expected = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, (received_sig or "").strip())
