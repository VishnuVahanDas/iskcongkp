# payment/utils.py
import base64, hmac, hashlib
from django.conf import settings

def basic_auth_header():
    # SmartGateway expects Authorization: Basic <base64(API_KEY)>
    # i.e., encode the API key itself (not "user:pass")
    # Ref: API docs “BasicAuth – Session” 
    api_key = settings.HDFC_SMART["API_KEY"].encode()
    return "Basic " + base64.b64encode(api_key).decode()

def verify_hmac(payload: dict, received_sig: str, fields_in_mac: list) -> bool:
    """
    Build the HMAC string from the same fields (in order) that SmartGateway signed.
    You configure fields_in_mac from the doc/sample (common: order_id, amount, status, merchant_id).
    """
    secret = (settings.HDFC_SMART["RESPONSE_KEY"] or "").encode()
    msg = "|".join("" if payload.get(k) is None else str(payload[k]) for k in fields_in_mac).encode()
    expected = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, (received_sig or "").strip())
