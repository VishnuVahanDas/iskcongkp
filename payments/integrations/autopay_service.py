"""
EaseBuzz UPI AutoPay service layer — Nitya Seva ONLY.

Implements the three autocollect/v1 API calls:
  1. generate_access_key  — register UPI AutoPay mandate
  2. send_debit_notification — pre-debit notification (48 hrs before debit)
  3. execute_debit           — execute the actual monthly debit

ALL hash computation is done via autopay_utils — never via easebuzz.py.
Auth hash goes in the Authorization header — NEVER in the POST body.
Base URL: https://api.easebuzz.in/autocollect/v1  (NOT pay.easebuzz.in)
"""

import uuid
import requests
import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from django.conf import settings
from .autopay_utils import hash_access_key, hash_notify, hash_execute

logger = logging.getLogger(__name__)


def _fmt_amount(amount) -> str:
    """Always format amount as float string with 2 decimals."""
    return "{:.2f}".format(float(amount))


def _headers_for(auth_hash: str) -> dict:
    return {
        "Authorization":     auth_hash,
        "X-EB-MERCHANT-KEY": settings.EASEBUZZ_KEY,
        "Content-Type":      "application/json",
    }


def generate_txnid() -> str:
    return f"NS{uuid.uuid4().hex[:12].upper()}"


def generate_access_key(txnid: str, amount, email: str,
                        phone: str, seva_type: str) -> dict:
    """
    Step 1: Generate access key for UPI AutoPay mandate registration.
    Returns dict with access_key on success.
    Raises Exception with EaseBuzz error message on failure.
    """
    amt_str    = _fmt_amount(amount)
    auth_hash  = hash_access_key(amt_str, txnid)
    start_date = date.today().strftime("%Y-%m-%d")
    end_date   = (date.today() + relativedelta(years=5)).strftime("%Y-%m-%d")

    payload = {
        "key":                        settings.EASEBUZZ_KEY,
        "transaction_id":             txnid,
        "success_url":                settings.NITYA_SEVA_SUCCESS_URL,
        "failure_url":                settings.NITYA_SEVA_FAILURE_URL,
        "request_type":               "SEAMLESS",
        "amount":                     float(amt_str),
        "email":                      email or "seva@holytrail.in",
        "phone":                      phone,
        "start_date":                 start_date,
        "end_date":                   end_date,
        "frequency":                  "monthly",
        "amount_rule":                "EXACT",
        "upfront_presentment_amount": "",
        "payment_modes":              ["UPIAD"],
        "udf1":                       seva_type,
        "udf2": "", "udf3": "", "udf4": "",
        "udf5": "", "udf6": "", "udf7": "",
    }

    headers = {
        **_headers_for(auth_hash),
        "X-EB-PAYMENT-MODE": "UPIAD",
    }

    logger.debug("[AutoPay] generate_access_key txnid=%s amt=%s", txnid, amt_str)

    resp = requests.post(
        settings.AUTOPAY_ACCESS_KEY_URL,
        json=payload, headers=headers, timeout=30,
    )
    data = resp.json()
    logger.debug("[AutoPay] generate_access_key response: %s", data)

    if not data.get("success"):
        raise Exception(
            f"AutoPay access key failed: {data.get('message', data)}"
        )
    return {
        "access_key": data["access_key"],
        "txnid":      txnid,
        "start_date": start_date,
        "end_date":   end_date,
    }


def send_debit_notification(txnid: str, amount,
                            notification_number: str) -> dict:
    """
    Step 2 (monthly): Send pre-debit notification 48 hrs before debit.
    notification_number must be unique per merchant per month.
    Returns dict with notification id on success.
    Raises Exception on failure.
    """
    amt_str   = _fmt_amount(amount)
    auth_hash = hash_notify(txnid, notification_number, amt_str)

    payload = {
        "key":                         settings.EASEBUZZ_KEY,
        "transaction_id":              txnid,
        "amount":                      float(amt_str),
        "notification_request_number": notification_number,
        "schedule_presentment":        False,
        "split_payments":              {},
    }

    logger.debug("[AutoPay] notify txnid=%s notif_num=%s", txnid, notification_number)

    resp = requests.post(
        settings.AUTOPAY_NOTIFY_URL,
        json=payload, headers=_headers_for(auth_hash), timeout=30,
    )
    data = resp.json()
    logger.debug("[AutoPay] notify response: %s", data)

    if not data.get("success"):
        raise Exception(
            f"AutoPay notify failed: {data.get('message', data)}"
        )
    return {
        "notification_id":     data["data"]["id"],
        "notification_status": data["data"]["status"],
    }


def execute_debit(txnid: str, amount, notification_id: str,
                  merchant_debit_number: str) -> dict:
    """
    Step 3 (monthly): Execute the actual debit after notification.
    merchant_debit_number must be unique per merchant.
    notification_id is the "id" from send_debit_notification response.
    Raises Exception on failure.
    """
    amt_str   = _fmt_amount(amount)
    auth_hash = hash_execute(txnid, merchant_debit_number, amt_str)

    payload = {
        "key":                         settings.EASEBUZZ_KEY,
        "transaction_id":              txnid,
        "amount":                      float(amt_str),
        "notification_request_number": notification_id,
        "merchant_request_number":     merchant_debit_number,
    }

    logger.debug("[AutoPay] execute txnid=%s deb_num=%s", txnid, merchant_debit_number)

    resp = requests.post(
        settings.AUTOPAY_EXECUTE_URL,
        json=payload, headers=_headers_for(auth_hash), timeout=30,
    )
    data = resp.json()
    logger.debug("[AutoPay] execute response: %s", data)

    if not data.get("success"):
        raise Exception(
            f"AutoPay execute failed: {data.get('message', data)}"
        )
    return {
        "pg_transaction_id":       data["data"]["pg_transaction_id"],
        "presentment_status":      data["data"]["status"],
        "merchant_request_number": merchant_debit_number,
    }
