try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs):
        return False
load_dotenv()

import os
import json
import re
import logging
from decimal import Decimal, ROUND_HALF_UP

import requests
from easebuzz_lib.easebuzz_payment_gateway import Easebuzz
from ..utils import _sanitize_order_id

EASEBUZZ_MERCHANT_KEY = os.getenv("EASEBUZZ_MERCHANT_KEY", "")
EASEBUZZ_SALT = os.getenv("EASEBUZZ_SALT", "")
_raw_env = os.getenv("EASEBUZZ_ENV", "test")
EASEBUZZ_ENV = _raw_env.split("#", 1)[0].strip().lower() or "test"  # test | prod
EASEBUZZ_DEBUG = os.getenv("EASEBUZZ_DEBUG", "false").lower() in ("1", "true", "yes")

logger = logging.getLogger(__name__)


class EasebuzzError(Exception):
    pass


# Backward-compatible alias used by payments.views
class EasebuzzIntegrationError(EasebuzzError):
    pass


def _amount_str(amount) -> str:
    try:
        q = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        # Easebuzz expects float with one or two decimals; keep two for safety
        return f"{q:.2f}"
    except Exception:
        raise EasebuzzError("Invalid amount value")


def _amount_hash_variants(amount_text: str) -> list[str]:
    """Return ordered unique amount representations for hash compatibility."""
    variants = [amount_text]
    try:
        dec = Decimal(amount_text)
        variants.append(format(dec.normalize(), "f"))
        variants.append(str(float(dec)))
    except Exception:
        pass

    seen = set()
    ordered = []
    for v in variants:
        if v in seen:
            continue
        seen.add(v)
        ordered.append(v)
    return ordered


def _client() -> Easebuzz:
    if not EASEBUZZ_MERCHANT_KEY:
        raise EasebuzzError("Missing EASEBUZZ_MERCHANT_KEY")
    if not EASEBUZZ_SALT:
        raise EasebuzzError("Missing EASEBUZZ_SALT")
    if not EASEBUZZ_ENV:
        raise EasebuzzError("Missing EASEBUZZ_ENV")
    return Easebuzz(EASEBUZZ_MERCHANT_KEY, EASEBUZZ_SALT, EASEBUZZ_ENV)


def create_payment_link(*, txn_id, amount, firstname, email, phone, productinfo,
                        surl, furl, udf=None, address=None, city="", state="",
                        country="India", zipcode="") -> dict:
    """Create Easebuzz payment link.

    Returns dict with keys: status, data (link), access_key (if any), raw.
    """
    udf = udf or {}
    address = address or {}
    if not firstname:
        firstname = "Devotee"
    if not email:
        raise EasebuzzError("Missing email")
    if not phone:
        raise EasebuzzError("Missing phone")
    phone_digits = re.sub(r"\D", "", str(phone))
    if len(phone_digits) >= 10:
        phone_digits = phone_digits[-10:]
    if len(phone_digits) < 10:
        raise EasebuzzError("Invalid phone number")
    if not productinfo:
        productinfo = "Donation"
    if not surl or not str(surl).startswith("https://"):
        raise EasebuzzError("Invalid success URL (surl)")
    if not furl or not str(furl).startswith("https://"):
        raise EasebuzzError("Invalid failure URL (furl)")

    post_data = {
        "txnid": _sanitize_order_id(txn_id),
        "firstname": firstname or "",
        "phone": phone_digits,
        "email": email,
        "amount": _amount_str(amount),
        "productinfo": productinfo,
        "surl": surl,
        "furl": furl,
        "city": city or "",
        "zipcode": zipcode or "",
        "address1": (address.get("address1") or address.get("address_line1") or ""),
        "address2": (address.get("address2") or address.get("address_line2") or ""),
        "state": state or "",
        "country": country or "India",
        "udf1": udf.get("udf1", ""),
        "udf2": udf.get("udf2", ""),
        "udf3": udf.get("udf3", ""),
        "udf4": udf.get("udf4", ""),
        "udf5": udf.get("udf5", ""),
    }
    try:
        result = _client().initiatePaymentAPI(post_data)
        data = json.loads(result or "{}")
    except Exception as e:
        raise EasebuzzError(f"Gateway request failed: {e}")

    if data.get("status") == 1:
        return {
            "ok": True,
            "status": 1,
            "data": data.get("data"),
            "access_key": data.get("access_key", ""),
            "raw": data,
        }
    if EASEBUZZ_DEBUG:
        safe_payload = {k: post_data.get(k) for k in (
            "txnid","amount","firstname","email","phone","productinfo","surl","furl",
            "city","state","country","zipcode","udf1","udf2","udf3","udf4","udf5"
        )}
        logger.error("Easebuzz create_payment_link failed. env=%s payload=%s response=%s",
                     EASEBUZZ_ENV, safe_payload, data)
    reason = data.get("data") or data.get("reason") or data
    raise EasebuzzError(f"Create payment failed: {reason}")


# Legacy helpers expected by payments.views
def initiate_payment(post_data: dict) -> dict:
    """Directly call Easebuzz initiatePaymentAPI with raw post_data."""
    try:
        # normalize a few required fields for the legacy endpoint
        if "amount" in post_data:
            post_data["amount"] = _amount_str(post_data["amount"])
        if "phone" in post_data:
            phone_digits = re.sub(r"\D", "", str(post_data.get("phone", "")))
            if len(phone_digits) >= 10:
                post_data["phone"] = phone_digits[-10:]
        result = _client().initiatePaymentAPI(post_data)
        data = json.loads(result or "{}")
    except Exception as e:
        raise EasebuzzIntegrationError(f"Gateway request failed: {e}")
    if data.get("status") != 1 and EASEBUZZ_DEBUG:
        safe_payload = {k: post_data.get(k) for k in (
            "txnid","amount","firstname","email","phone","productinfo","surl","furl",
            "city","state","country","zipcode","udf1","udf2","udf3","udf4","udf5"
        )}
        logger.error("Easebuzz initiate_payment failed. env=%s payload=%s response=%s",
                     EASEBUZZ_ENV, safe_payload, data)
    return data


def parse_gateway_response(params) -> dict:
    """Verify response hash and return response dict."""
    try:
        return verify_response(params)
    except EasebuzzError as e:
        raise EasebuzzIntegrationError(str(e))


def verify_response(params) -> dict:
    """Verify response hash and return Easebuzz response dict."""
    try:
        result = _client().easebuzzResponse(params)
    except Exception as e:
        raise EasebuzzError(f"Response verification failed: {e}")
    if isinstance(result, str):
        try:
            return json.loads(result)
        except Exception:
            return {"status": 0, "data": "Invalid response format"}
    return result


def transaction_lookup(*, txn_id, amount, phone, email) -> dict:
    """Query transaction details to confirm payment."""
    post_data = {
        "txnid": _sanitize_order_id(txn_id),
        "amount": _amount_str(amount),
        "phone": phone or "",
        "email": email or "",
    }
    try:
        result = _client().transactionAPI(post_data)
        data = json.loads(result or "{}")
    except Exception as e:
        raise EasebuzzError(f"Transaction lookup failed: {e}")
    return data
