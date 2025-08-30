# payments/hdfc_client.py
import json
import requests
from decimal import Decimal
from django.conf import settings
from requests.auth import HTTPBasicAuth
from jwcrypto import jwk, jwe, jws
from jwcrypto.common import json_encode

COMMON_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Some endpoints may still accept Basic Auth (status/refund).
basic_auth = HTTPBasicAuth(settings.HDFC_MERCHANT_ID, settings.HDFC_API_KEY)

def _sign_payload_rs256(payload: dict) -> str:
    """
    Create a compact JWS (RS256) with 'kid' header using the merchant private key.
    """
    priv = jwk.JWK.from_pem(settings.HDFC_MERCHANT_PRIVATE_KEY_PEM.encode())
    signer = jws.JWS(json.dumps(payload).encode("utf-8"))
    signer.add_signature(
        priv,
        alg="RS256",
        protected=json_encode({
            "alg": "RS256",
            "kid": settings.HDFC_JWT_KID,
            "typ": "JWT",
        }),
    )
    return signer.serialize(compact=True)

def _encrypt_jwe(jws_compact: str) -> str:
    """
    Encrypt the JWS using Bank's public key (RSA-OAEP-256 + A256GCM) to produce compact JWE.
    """
    pub = jwk.JWK.from_pem(settings.HDFC_BANK_PUBLIC_KEY_PEM.encode())
    token = jwe.JWE(
        plaintext=jws_compact.encode("utf-8"),
        protected=json_encode({
            "alg": "RSA-OAEP-256",
            "enc": "A256GCM",
            "typ": "JWE",
        }),
    )
    token.add_recipient(pub)
    return token.serialize(compact=True)

def create_session(payload: dict) -> dict:
    """
    SmartGateway /v4/session expects body {"jwt": "<JWE of JWS(payload)>"}
    """
    # Ensure required fields are well-formed
    payload = dict(payload)
    payload["merchant_id"] = settings.HDFC_MERCHANT_ID
    if "amount" in payload:
        payload["amount"] = f"{Decimal(str(payload['amount'])):.2f}"
    payload.setdefault("currency", "INR")

    # 1) JWS (RS256 with merchant private key + kid)
    jws_token = _sign_payload_rs256(payload)
    # 2) JWE (encrypt with bank public key)
    jwe_token = _encrypt_jwe(jws_token)

    body = {"jwt": jwe_token}
    url = f"{settings.HDFC_BASE_URL}/v4/session"
    resp = requests.post(url, json=body, headers=COMMON_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()

def order_status(order_id: str) -> dict:
    """
    If this returns 'JWT required' or 401, we’ll switch it to JWS+JWE like create_session.
    """
    url = f"{settings.HDFC_BASE_URL}/v4/orders/{order_id}"
    resp = requests.get(url, headers=COMMON_HEADERS, auth=basic_auth, timeout=30)
    resp.raise_for_status()
    return resp.json()

def refund_order(order_id: str, payload: dict) -> dict:
    """
    If refund also requires JWT, wrap similarly (sign+encrypt) and POST {"jwt": "..."}.
    """
    url = f"{settings.HDFC_BASE_URL}/v4/orders/{order_id}/refunds"
    resp = requests.post(url, json=payload or {}, headers=COMMON_HEADERS, auth=basic_auth, timeout=30)
    resp.raise_for_status()
    return resp.json()
