import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth

auth = HTTPBasicAuth(settings.HDFC_MERCHANT_ID, settings.HDFC_API_KEY)

COMMON_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

def create_session(payload: dict) -> dict:
    """
    Call SmartGateway Session API to create an order/session and get the redirect URL.
    """
    r = requests.post(settings.HDFC_SESSION_URL, json=payload, headers=COMMON_HEADERS, auth=auth, timeout=30)
    r.raise_for_status()
    return r.json()

def order_status(order_id: str) -> dict:
    url = settings.HDFC_ORDER_STATUS_URL.format(order_id=order_id)
    r = requests.get(url, headers=COMMON_HEADERS, auth=auth, timeout=30)
    r.raise_for_status()
    return r.json()

def refund_order(order_id: str, payload: dict) -> dict:
    url = settings.HDFC_REFUND_URL.format(order_id=order_id)
    r = requests.post(url, json=payload, headers=COMMON_HEADERS, auth=auth, timeout=30)
    r.raise_for_status()
    return r.json()
