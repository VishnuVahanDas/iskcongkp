import logging
from typing import Iterable, List

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _fail_silently() -> bool:
    return getattr(settings, "EMAIL_FAIL_SILENTLY", True)


def _admin_recipients() -> List[str]:
    # Comma-separated list via env or settings; fall back to DEFAULT_FROM_EMAIL/host user
    raw = getattr(settings, "PAYMENTS_ADMIN_EMAILS", None) or getattr(settings, "ADMIN_EMAILS", None)
    if not raw:
        raw = ",".join([
            getattr(settings, "EMAIL_HOST_USER", "") or "",
            getattr(settings, "DEFAULT_FROM_EMAIL", "") or "",
        ])
    emails = [e.strip() for e in (raw or "").split(",") if e and e.strip()]
    # Deduplicate while preserving order
    seen = set()
    uniq: List[str] = []
    for e in emails:
        if e.lower() not in seen:
            seen.add(e.lower())
            uniq.append(e)
    return uniq


def send_payment_confirmation(*, order) -> None:
    """Send a receipt to the customer and a notification to admins for a paid order.

    Expects an Order model instance with fields used below.
    """
    try:
        # Build context
        meta = order.metadata or {}
        context = {
            "order_id": order.order_id,
            "bank_order_id": order.bank_order_id,
            "amount": order.amount,
            "currency": order.currency,
            "status": order.status,
            "customer_id": order.customer_id,
            "customer_email": order.customer_email,
            "customer_phone": order.customer_phone,
            "description": meta.get("description", "Donation"),
        }

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)

        # Customer receipt
        try:
            if order.customer_email:
                cust_subject = f"Payment received: {order.order_id} – {order.currency} {order.amount}"
                cust_html = render_to_string("emails/payment_receipt_customer.html", context)
                cust_text = render_to_string("emails/payment_receipt_customer.txt", context)
                msg = EmailMultiAlternatives(cust_subject, cust_text, from_email, [order.customer_email])
                msg.attach_alternative(cust_html, "text/html")
                msg.send(fail_silently=_fail_silently())
        except Exception:
            logger.exception("Failed to send payment receipt to %s", order.customer_email)

        # Admin notification
        try:
            admins = _admin_recipients()
            if admins:
                admin_subject = f"New payment: {order.order_id} – {order.currency} {order.amount} ({order.status})"
                admin_html = render_to_string("emails/payment_notification_admin.html", context)
                admin_text = render_to_string("emails/payment_notification_admin.txt", context)
                msg = EmailMultiAlternatives(admin_subject, admin_text, from_email, admins)
                msg.attach_alternative(admin_html, "text/html")
                msg.send(fail_silently=_fail_silently())
        except Exception:
            logger.exception("Failed to send payment admin notification for %s", order.order_id)

    except Exception:
        logger.exception("send_payment_confirmation crashed for order=%s", getattr(order, "order_id", None))

