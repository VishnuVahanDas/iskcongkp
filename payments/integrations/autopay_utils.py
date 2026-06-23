"""
Hash utilities for EaseBuzz UPI AutoPay (autocollect/v1) APIs.
Isolated from the regular EaseBuzz payment gateway hash logic.

THREE DISTINCT HASH SEQUENCES — never mix them up:
  access_key : key | amount | transaction_id | salt
  notify     : key | transaction_id | notification_request_number | amount | salt
  execute    : key | transaction_id | merchant_request_number | amount | salt

Hash goes in the Authorization HTTP header — NEVER in the POST body.
Base URL is api.easebuzz.in — NEVER pay.easebuzz.in.
"""

import hashlib
from django.conf import settings


def _sha512(s: str) -> str:
    return hashlib.sha512(s.encode("utf-8")).hexdigest()


def hash_access_key(amount: str, transaction_id: str) -> str:
    """
    Hash for Generate Access Key API.
    Sequence: key | amount | transaction_id | salt
    """
    seq = f"{settings.EASEBUZZ_KEY}|{amount}|{transaction_id}|{settings.EASEBUZZ_SALT}"
    return _sha512(seq)


def hash_notify(transaction_id: str, notification_request_number: str,
                amount: str) -> str:
    """
    Hash for Pre-Debit Notification API.
    Sequence: key | transaction_id | notification_request_number | amount | salt
    """
    seq = (
        f"{settings.EASEBUZZ_KEY}|{transaction_id}|"
        f"{notification_request_number}|{amount}|{settings.EASEBUZZ_SALT}"
    )
    return _sha512(seq)


def hash_execute(transaction_id: str, merchant_request_number: str,
                 amount: str) -> str:
    """
    Hash for Execute Debit API.
    Sequence: key | transaction_id | merchant_request_number | amount | salt
    """
    seq = (
        f"{settings.EASEBUZZ_KEY}|{transaction_id}|"
        f"{merchant_request_number}|{amount}|{settings.EASEBUZZ_SALT}"
    )
    return _sha512(seq)
