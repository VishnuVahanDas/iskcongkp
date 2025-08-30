# payments/hdfc_client.py
import os, json, time, uuid
import requests
from decimal import Decimal
from django.conf import settings
from requests.auth import HTTPBasicAuth
from jwcrypto import jwk, jwe, jws
from jwcrypto.common import json_encode

COMMON_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}
basic_auth = HTTPBasicAuth(settings.HDFC_MERCHANT_ID, settings.HDFC_API_KEY)

# ---------- Key loaders ----------
def _load_priv() -> jwk.JWK:
    """
    Load merchant private key (bytes from settings). Supports optional passphrase.
    """
    if isinstance(settings.HDFC_MERCHANT_PRIVATE_KEY_PEM, (bytes, bytearray)):
        pem_bytes = settings.HDFC_MERCHANT_PRIVATE_KEY_PEM
    else:
        pem_bytes = str(settings.HDFC_MERCHANT_PRIVATE_KEY_PEM).encode("utf-8")
    pem_bytes = pem_bytes.replace(b"\r\n", b"\n")
    password = getattr(settings, "HDFC_MERCHANT_PRIVATE_KEY_PASSPHRASE", None)
    return jwk.JWK.from_pem(pem_bytes, password=None if not password else password.encode("utf-8"))

def _load_bank_pub() -> jwk.JWK:
    """
    Load Bank public key (bytes from settings).
    """
    if isinstance(settings.HDFC_BANK_PUBLIC_KEY_PEM, (bytes, bytearray)):
        pem_bytes = settings.HDFC_BANK_PUBLIC_KEY_PEM
    else:
        pem_bytes = str(settings.HDFC_BANK_PUBLIC_KEY_PEM).encode("utf-8")
    pem_bytes = pem_bytes.replace(b"\r\n", b"\n")
    return jwk.JWK.from_pem(pem_bytes)

# ---------- JWT utils ----------
def _sign_rs256_with_claims(payload: dict) -> tuple[str, dict]:
    """
    Add standard claims (iss, sub, iat, exp, jti), sign RS256 with merchant private key and kid.
    Returns (compact_jws, claims_used).
    """
    now = int(time.time())
    claims = {
        **payload,
        "iss": settings.HDFC_MERCHANT_ID,
        "sub": settings.HDFC_MERCHANT_ID,
        "iat": now,
        "exp": now + 300,  # 5 minutes
        "jti": str(uuid.uuid4()),
    }
    priv = _load_priv()
    signer = jws.JWS(json.dumps(claims).encode("utf-8"))
    signer.add_signature(
        priv,
        alg="RS256",
        protected=json_encode({"alg": "RS256", "kid": settings.HDFC_KEY_UUID, "typ": "JWT"}),
    )
    return signer.serialize(compact=True), claims

def _encrypt_jwe(jws_compact: str) -> str:
    """
    Encrypt JWS with Bank public key into compact JWE (RSA-OAEP-256 + A256GCM).
    """
    pub = _load_bank_pub()
    token = jwe.JWE(
        plaintext=jws_compact.encode("utf-8"),
        protected=json_encode({"alg": "RSA-OAEP-256", "enc": "A256GCM", "typ": "JWE"}),
    )
    token.add_recipient(pub)
    return token.serialize(compact=True)

def decrypt_and_verify_hdfc_response(body: dict) -> dict:
    """
    HDFC encrypted response format:
      header, encryptedKey, iv, encryptedPayload, tag
    1) Decrypt JWE with merchant private key
    2) Verify inner JWS with Bank public key
    3) Return parsed JWS payload (dict)
    """
    jwe_obj = jwe.JWE()
    jwe_obj.deserialize(json.dumps({
        "protected": body["header"],
        "encrypted_key": body["encryptedKey"],
        "iv": body["iv"],
        "ciphertext": body["encryptedPayload"],
        "tag": body["tag"],
    }))
    jwe_obj.decrypt(_load_priv())
    decrypted = jwe_obj.payload.decode("utf-8")

    jws_body = json.loads(decrypted)  # {"header": "...", "payload": "...", "signature": "..."}
    compact_jws = f"{jws_body['header']}.{jws_body['payload']}.{jws_body['signature']}"

    jws_obj = jws.JWS()
    jws_obj.deserialize(compact_jws)
    jws_obj.verify(_load_bank_pub())

    return json.loads(jws_obj.payload)

# ---------- API calls ----------
def create_session(payload: dict) -> dict:
    """
    POST {"jwt": JWE(JWS(payload))} -> /v4/session
    Auto-decrypts response if it comes encrypted.
    """
    body = dict(payload)
    body["merchant_id"] = settings.HDFC_MERCHANT_ID
    body.setdefault("currency", "INR")
    if "amount" in body:
        body["amount"] = f"{Decimal(str(body['amount'])):.2f}"

    jws_token, claims = _sign_rs256_with_claims(body)
    # (optional) minimal debug
    try:
        print("HDFC DEBUG -> kid:", settings.HDFC_KEY_UUID, "| iss:", claims.get("iss"), "| iat:", claims.get("iat"))
    except Exception:
        pass

    jwe_token = _encrypt_jwe(jws_token)
    url = f"{settings.HDFC_BASE_URL}/v4/session"
    resp = requests.post(url, json={"jwt": jwe_token}, headers=COMMON_HEADERS, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    # If encrypted response, decrypt & verify:
    if all(k in data for k in ("header", "encryptedKey", "iv", "encryptedPayload", "tag")):
        data = decrypt_and_verify_hdfc_response(data)

    return data

def order_status(order_id: str) -> dict:
    """
    If your tenant requires JWT here too, mirror create_session (sign+encrypt and POST {"jwt": ...}).
    """
    url = f"{settings.HDFC_BASE_URL}/v4/orders/{order_id}"
    resp = requests.get(url, headers=COMMON_HEADERS, auth=basic_auth, timeout=30)
    resp.raise_for_status()
    return resp.json()

def refund_order(order_id: str, payload: dict) -> dict:
    """
    If refund requires JWT on your tenant, switch to sign+encrypt as above.
    """
    url = f"{settings.HDFC_BASE_URL}/v4/orders/{order_id}/refunds"
    resp = requests.post(url, json=payload or {}, headers=COMMON_HEADERS, auth=basic_auth, timeout=30)
    resp.raise_for_status()
    return resp.json()
