"""
Celery tasks for EaseBuzz UPI AutoPay — Nitya Seva monthly debit cycle.

Schedule (add to settings.CELERY_BEAT_SCHEDULE):
  28th of every month, 10:00 IST — send_monthly_debit_notifications
  30th of every month, 10:00 IST — execute_monthly_debits

EaseBuzz requires the pre-debit notification to be sent at least
48 hours before the actual debit execution.
"""

from celery import shared_task
from django.utils import timezone


@shared_task
def send_monthly_debit_notifications():
    """
    Run this task on the 28th of every month.
    Sends pre-debit notification to all active Nitya Seva mandates.
    EaseBuzz requires notification 48 hrs before debit.
    """
    from .models import NityaSevaMandate  # noqa: avoid circular import at module level
    from payments.integrations.autopay_service import send_debit_notification
    import logging

    log = logging.getLogger(__name__)
    now   = timezone.now()
    year  = now.year
    month = now.month

    mandates = NityaSevaMandate.objects.filter(mandate_status="active")

    for mandate in mandates:
        notif_number = f"NTF{mandate.txnid}{year}{month:02d}"
        try:
            result = send_debit_notification(
                mandate.txnid, mandate.amount, notif_number,
            )
            mandate.last_notification_id     = result["notification_id"]
            mandate.last_notification_number = notif_number
            mandate.last_debit_status        = "notified"
            mandate.save(update_fields=[
                "last_notification_id",
                "last_notification_number",
                "last_debit_status",
            ])
        except Exception as e:
            log.error("AutoPay notify failed for %s: %s", mandate.txnid, e)


@shared_task
def execute_monthly_debits():
    """
    Run this task on the 30th of every month.
    Executes actual debit for all mandates that were notified.
    Must run at least 48 hrs after send_monthly_debit_notifications.
    """
    from .models import NityaSevaMandate  # noqa: avoid circular import at module level
    from payments.integrations.autopay_service import execute_debit
    import logging

    log = logging.getLogger(__name__)
    now   = timezone.now()
    year  = now.year
    month = now.month

    mandates = NityaSevaMandate.objects.filter(
        mandate_status="active",
        last_debit_status="notified",
    )

    for mandate in mandates:
        debit_number = f"DEB{mandate.txnid}{year}{month:02d}"
        try:
            result = execute_debit(
                mandate.txnid,
                mandate.amount,
                mandate.last_notification_id,
                debit_number,
            )
            mandate.last_debit_number   = debit_number
            mandate.last_debit_status   = "in_process"
            mandate.last_debit_pg_txnid = result["pg_transaction_id"]
            mandate.last_debited_at     = now
            mandate.save(update_fields=[
                "last_debit_number",
                "last_debit_status",
                "last_debit_pg_txnid",
                "last_debited_at",
            ])
        except Exception as e:
            log.error("AutoPay debit failed for %s: %s", mandate.txnid, e)
