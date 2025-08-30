import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from payments.models import Order
from payments.integrations.hdfc import get_order_status, HdfcError

class Command(BaseCommand):
    help = "Poll HDFC Order Status for pending orders and update local DB"

    def add_arguments(self, parser):
        parser.add_argument("--max", type=int, default=50)
        parser.add_argument("--sleep", type=float, default=0.5)
        parser.add_argument("--older-than-minutes", type=int, default=1)

    def handle(self, *args, **opts):
        cutoff = timezone.now() - timezone.timedelta(minutes=opts["older_than_minutes"])
        qs = Order.objects.filter(status__in=["NEW", "PENDING", "AUTHORIZED"]).filter(updated_at__lt=cutoff).order_by("updated_at")[:opts["max"]]

        if not qs.exists():
            self.stdout.write(self.style.SUCCESS("No pending orders to reconcile."))
            return

        for o in qs:
            try:
                result = get_order_status(o.order_id, o.customer_id)
                data = result["data"]
                o.status = str(data.get("status", o.status or ""))
                o.bank_order_id = data.get("id", o.bank_order_id or "")
                o.txn_id = data.get("txn_id", o.txn_id or "")
                o.payment_method_type = data.get("payment_method_type", o.payment_method_type or "")
                o.payment_method = data.get("payment_method", o.payment_method or "")
                o.auth_type = data.get("auth_type", o.auth_type or "")
                o.refunded = bool(data.get("refunded", o.refunded))
                try:
                    o.amount_refunded = data.get("amount_refunded", o.amount_refunded)
                except Exception:
                    pass
                o.last_status_payload = data
                o.save()
                self.stdout.write(self.style.SUCCESS(f"Updated {o.order_id} -> {o.status}"))
            except HdfcError as e:
                self.stdout.write(self.style.WARNING(f"{o.order_id}: {e}"))
            time.sleep(opts["sleep"])
