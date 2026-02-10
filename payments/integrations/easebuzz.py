import json
import os
from typing import Any, Dict, Mapping

try:
    from easebuzz_lib.easebuzz_payment_gateway import Easebuzz
except Exception:  # library is optional until integrator adds it
    Easebuzz = None


class EasebuzzIntegrationError(Exception):
    pass


def _credentials() -> tuple[str, str, str]:
    merchant_key = os.getenv("EASEBUZZ_MERCHANT_KEY", "")
    salt = os.getenv("EASEBUZZ_SALT", "")
    env = os.getenv("EASEBUZZ_ENV", "test")
    if not merchant_key or not salt:
        raise EasebuzzIntegrationError("Missing EASEBUZZ_MERCHANT_KEY or EASEBUZZ_SALT")
    if env not in {"test", "prod"}:
        raise EasebuzzIntegrationError("EASEBUZZ_ENV must be either 'test' or 'prod'")
    return merchant_key, salt, env


def _client():
    if Easebuzz is None:
        raise EasebuzzIntegrationError(
            "easebuzz_lib is not installed. Copy easebuzz_lib into project root as per integration guide."
        )
    merchant_key, salt, env = _credentials()
    return Easebuzz(merchant_key, salt, env)


def initiate_payment(post_data: Mapping[str, Any]) -> Dict[str, Any]:
    response = _client().initiatePaymentAPI(dict(post_data))
    if isinstance(response, str):
        return json.loads(response)
    if isinstance(response, dict):
        return response
    raise EasebuzzIntegrationError("Unexpected response type from initiatePaymentAPI")


def parse_gateway_response(post_data: Mapping[str, Any]) -> Any:
    return _client().easebuzzResponse(dict(post_data))
