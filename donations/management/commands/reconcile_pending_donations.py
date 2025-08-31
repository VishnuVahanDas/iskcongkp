from django.core.management.base import BaseCommand
from django.utils import timezone

from donations.models import Donation
from donations.services import mark_paid_and_receipt, issue_magic_link
from donations.emails import send_receipt_email
from payments.integrations.hdfc import get_order_status, HdfcError


def _norm_status(data: dict) -> str:
    try:
        s = (
            (data or {}).get("status")
            or (data or {}).get("result", {}).get("status")
            or (data or {}).get("order", {}).get("status")
            or (data or {}).get("payment", {}).get("status")
            or (data or {}).get("transaction", {}).get("status")
            or ""
        )
        return str(s).upper()
    except Exception:
        return ""


class Command(BaseCommand):
    help = "Reconcile PENDING donations against HDFC by polling order status"

    def add_arguments(self, parser):
        parser.add_argument("--max", type=int, default=100, help="Max donations to process")
        parser.add_argument("--minutes", type=int, default=120, help="Only donations created within last N minutes (0=all)")

    def handle(self, *args, **opts):
        qs = Donation.objects.filter(status="PENDING").order_by("created_at")
        if opts["minutes"] > 0:
            cutoff = timezone.now() - timezone.timedelta(minutes=opts["minutes"])
            qs = qs.filter(created_at__gte=cutoff)

        cnt = 0
        ok = 0
        for d in qs[: opts["max"]]:
            cnt += 1
            # We used our txn_id as the HDFC order_id
            order_id = d.txn_id
            customer_id = d.donor.email or d.donor.phone_e164 or f"donor-{d.donor_id}"
            try:
                result = get_order_status(order_id, customer_id)
                data = result.get("data") or {}
                status = _norm_status(data)
                if status in {"CHARGED", "SUCCESS", "SUCCESSFUL", "PAID", "CAPTURED", "COMPLETED", "SETTLED"}:
                    mode = data.get("payment_method") or data.get("payment_method_type") or ""
                    mark_paid_and_receipt(d, mode, data)
                    # send receipt + magic link once
                    meta = d.gateway_meta or {}
                    if not bool(meta.get("receipt_email_sent")):
                        try:
                            mlt = issue_magic_link(d.donor)
                            from django.urls import reverse
                            from django.contrib.sites.models import Site
                            domain = Site.objects.get_current().domain
                            link = f"https://{domain}" + reverse("donations:magic_claim", kwargs={"token": mlt.token})
                            send_receipt_email(d, magic_link_url=link)
                            meta["receipt_email_sent"] = True
                            d.gateway_meta = meta
                            d.save(update_fields=["gateway_meta"])
                        except Exception:
                            pass
                    ok += 1
                    self.stdout.write(self.style.SUCCESS(f"Donation {d.txn_id} -> SUCCESS"))
                else:
                    self.stdout.write(f"Donation {d.txn_id}: status={status or 'UNKNOWN'}")
            except HdfcError as e:
                self.stdout.write(self.style.WARNING(f"{d.txn_id}: {e}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"{d.txn_id}: error {e}"))

        self.stdout.write(self.style.SUCCESS(f"Checked {cnt}, updated {ok} donations."))

