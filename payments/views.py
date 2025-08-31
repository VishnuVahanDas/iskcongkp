import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from datetime import timezone

from .integrations.hdfc import create_session, get_order_status, HdfcError, _sanitize_order_id
from django.utils.crypto import get_random_string
from .emails import send_payment_confirmation
from .models import Order

def _json_body(request):
    try: return json.loads(request.body.decode("utf-8"))
    except Exception: return None

def hdfc_test_page_view(request):
    """Render a simple test page to initiate an HDFC payment session.

    Prefills customer info from the logged-in user's profile (Customer).
    """
    ctx = {}
    if request.user.is_authenticated:
        try:
            ctx["mobile"] = getattr(request.user.customer, "phone", "") or ""
        except Exception:
            ctx["mobile"] = ""
    return render(request, "payments/hdfc_test.html", ctx)


@login_required
def my_payments_view(request):
    """List previous payments for the logged-in customer."""
    # Determine the user's customer_id; default to username
    cust_id = getattr(getattr(request.user, "customer", None), "customer_id", None) or request.user.username
    qs = Order.objects.filter(customer_id=cust_id).order_by("-created_at")

    # Very light pagination
    try:
        page = int(request.GET.get("page", "1"))
        if page < 1: page = 1
    except Exception:
        page = 1
    page_size = 10
    start = (page - 1) * page_size
    end = start + page_size
    total = qs.count()
    items = list(qs[start:end])
    has_next = end < total
    has_prev = start > 0

    ctx = {
        "orders": items,
        "page": page,
        "has_next": has_next,
        "has_prev": has_prev,
        "next_page": page + 1,
        "prev_page": page - 1,
        "customer_id": cust_id,
    }
    return render(request, "payments/my_payments.html", ctx)

@csrf_exempt
@require_POST
def hdfc_create_session_view(request):
    body = _json_body(request)
    if not body:
        return HttpResponseBadRequest("Invalid JSON body")
    required = ["order_id", "amount", "customer_id", "customer_email", "customer_phone"]
    missing = [k for k in required if not body.get(k)]
    if missing:
        return HttpResponseBadRequest(f"Missing fields: {', '.join(missing)}")

    # Normalize order_id to match gateway and DB constraints (<=20 alnum)
    raw_oid = str(body.get("order_id", ""))
    oid = _sanitize_order_id(raw_oid)
    if not oid:
        return HttpResponseBadRequest("order_id must contain alphanumeric characters (max 20)")
    # Ensure uniqueness in our DB to avoid reusing a previously paid order_id
    # If duplicate, tweak last 2 chars with a random suffix while keeping <=20 alnum
    try:
        max_attempts = 5
        attempts = 0
        base = oid
        while Order.objects.filter(order_id=oid).exists() and attempts < max_attempts:
            suffix = get_random_string(2, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            if len(base) >= 20:
                oid = (base[:18] + suffix)
            else:
                oid = (base + suffix)[:20]
            attempts += 1
    except Exception:
        pass

    try:
        result = create_session(
            order_id=oid,
            amount=body["amount"],
            customer_id=body["customer_id"],
            customer_email=body["customer_email"],
            customer_phone=body["customer_phone"],
            first_name=body.get("first_name", ""),
            last_name=body.get("last_name", ""),
            description=body.get("description", ""),
            currency=body.get("currency", "INR"),
        )
        data = result["data"]
        bank_id = data.get("id") or ""
        links = data.get("payment_links", {}) or {}
        sdk = data.get("sdk_payload", None)

        Order.objects.update_or_create(
            order_id=oid,
            defaults={
                "bank_order_id": bank_id,
                "status": str(data.get("status", "NEW")),
                "amount": body["amount"],
                "currency": body.get("currency", "INR"),
                "customer_id": body["customer_id"],
                "customer_email": body["customer_email"],
                "customer_phone": body["customer_phone"],
                "payment_links_web": links.get("web", "") or links.get("mobile", "") or "",
                "sdk_payload": sdk,
                # persist description in metadata so receipts include purpose
                "metadata": {"payment_links": links, "description": body.get("description", "Donation")},
            },
        )

        resp = JsonResponse(result, status=200, safe=False)
        resp.set_cookie("hdfc_last_order_id", oid, max_age=1800, secure=True, samesite="Lax")
        resp.set_cookie("hdfc_customer_id", body["customer_id"], max_age=1800, secure=True, samesite="Lax")
        return resp

    except HdfcError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400, safe=False)
    except Exception as e:
        # Ensure JSON error instead of HTML 500 page for the test client
        return JsonResponse({"ok": False, "error": f"Server error: {str(e)}"}, status=500, safe=False)

@require_GET
def hdfc_order_status_view(request, order_id: str):
    oid = _sanitize_order_id(order_id)
    customer_id = request.GET.get("customer_id", "")
    if not customer_id:
        return HttpResponseBadRequest("customer_id is required")

    def _extract_status(data: dict) -> str:
        # Normalize status from various possible keys/locations
        if not isinstance(data, dict):
            return ""
        s = (data.get("status") or
             (data.get("order") or {}).get("status") or
             (data.get("payment") or {}).get("status") or
             (data.get("transaction") or {}).get("status") or
             (data.get("result") or {}).get("status") or
             "")
        return str(s).upper()

    try:
        result = get_order_status(oid, customer_id)
        data = result["data"]

        # persist
        try:
            order = Order.objects.get(order_id=oid)
        except Order.DoesNotExist:
            order = None

        if order:
            order.status = str(data.get("status", order.status or ""))
            order.bank_order_id = data.get("id", order.bank_order_id or "")
            order.txn_id = data.get("txn_id", order.txn_id or "")
            order.payment_method_type = data.get("payment_method_type", order.payment_method_type or "")
            order.payment_method = data.get("payment_method", order.payment_method or "")
            order.auth_type = data.get("auth_type", order.auth_type or "")
            order.refunded = bool(data.get("refunded", order.refunded))
            try:
                order.amount_refunded = data.get("amount_refunded", order.amount_refunded)
            except Exception:
                pass
            order.last_status_payload = data

            iso = data.get("order_expiry") or (data.get("metadata") or {}).get("order_expiry")
            if iso:
                dt = parse_datetime(iso)
                if dt and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                order.order_expiry = dt

            # Mark description if we get it back in metadata or leave existing
            meta = order.metadata or {}
            if (data.get("description") and not meta.get("description")):
                meta["description"] = data.get("description")
            order.metadata = meta
            order.save()

        norm_status = _extract_status(data)
        success_statuses = {"CHARGED", "SUCCESS", "SUCCESSFUL", "PAID", "CAPTURED", "COMPLETED", "SETTLED"}
        paid = norm_status in success_statuses
        result["is_paid"] = paid

        # Send confirmation emails once per paid order using a row-level lock to avoid duplicates
        if paid and order:
            from django.db import transaction
            try:
                should_send = False
                with transaction.atomic():
                    locked = Order.objects.select_for_update().get(pk=order.pk)
                    meta = locked.metadata or {}
                    if not bool(meta.get("receipt_sent")):
                        meta["receipt_sent"] = True
                        locked.metadata = meta
                        locked.save(update_fields=["metadata"])
                        should_send = True
                if should_send:
                    # Send after commit to avoid emailing on rolled-back tx
                    try:
                        from django.db import transaction as _tx
                        _tx.on_commit(lambda: send_payment_confirmation(order=order))
                    except Exception:
                        send_payment_confirmation(order=order)
            except Exception:
                # Never break the status API due to email logic
                pass

        # Reconcile Donations app if webhook missed: mark SUCCESS and send receipt/magic link
        try:
            if paid:
                from donations.models import Donation
                donation = (
                    Donation.objects.filter(txn_id=oid).first() or
                    Donation.objects.filter(order_id=data.get("id") or "").first() or
                    Donation.objects.filter(txn_id=data.get("txn_id") or "").first()
                )
                if donation and donation.status != "SUCCESS":
                    from donations.services import mark_paid_and_receipt, issue_magic_link
                    from django.urls import reverse
                    from donations.emails import send_receipt_email

                    mode = data.get("payment_method") or data.get("payment_method_type") or ""
                    mark_paid_and_receipt(donation, mode, data)
                    # send receipt + magic link once
                    try:
                        mlt = issue_magic_link(donation.donor)
                        link = request.build_absolute_uri(
                            reverse("donations:magic_claim", kwargs={"token": mlt.token})
                        )
                        send_receipt_email(donation, magic_link_url=link)
                        meta = donation.gateway_meta or {}
                        meta["receipt_email_sent"] = True
                        meta["reconciled_via"] = "payments_status_api"
                        donation.gateway_meta = meta
                        donation.save(update_fields=["gateway_meta"])
                    except Exception:
                        # Mark that we attempted; avoid crashing status API
                        pass
        except Exception:
            # Never break status API due to cross-app reconciliation
            pass

        return JsonResponse(result, status=200, safe=False)

    except HdfcError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400, safe=False)

@csrf_exempt
def hdfc_return_view(request):
    order_id = request.POST.get("order_id") or request.GET.get("order_id") or ""
    customer_id = request.POST.get("customer_id") or request.GET.get("customer_id") or ""

    # Default context
    ctx = {"order_id": order_id, "customer_id": customer_id, "server_checked": False, "is_paid": False, "status": ""}
    
    # If customer_id missing, try to fetch from our DB by order_id
    if order_id and not customer_id:
        try:
            o = Order.objects.filter(order_id=_sanitize_order_id(order_id)).first()
            if o and o.customer_id:
                customer_id = o.customer_id
                ctx["customer_id"] = customer_id
        except Exception:
            pass
        
    # Server-side reconciliation for reliability (single source of truth)
    if order_id and customer_id:
        try:
            result = get_order_status(_sanitize_order_id(order_id), customer_id)
            data = result.get("data") or {}

            # Normalize success state
            def _extract_status(d: dict) -> str:
                s = (
                    (d or {}).get("status")
                    or (d or {}).get("order", {}).get("status")
                    or (d or {}).get("payment", {}).get("status")
                    or (d or {}).get("transaction", {}).get("status")
                    or (d or {}).get("result", {}).get("status")
                    or ""
                )
                return str(s).upper()

            norm_status = _extract_status(data)
            success_statuses = {"CHARGED", "SUCCESS", "SUCCESSFUL", "PAID", "CAPTURED", "COMPLETED", "SETTLED"}
            paid = norm_status in success_statuses
            ctx.update({"server_checked": True, "is_paid": paid, "status": norm_status})

            # Persist to payments.Order table
            try:
                order = Order.objects.get(order_id=_sanitize_order_id(order_id))
                order.status = str(data.get("status", order.status or ""))
                order.bank_order_id = data.get("id", order.bank_order_id or "")
                order.txn_id = data.get("txn_id", order.txn_id or "")
                order.payment_method_type = data.get("payment_method_type", order.payment_method_type or "")
                order.payment_method = data.get("payment_method", order.payment_method or "")
                order.auth_type = data.get("auth_type", order.auth_type or "")
                order.last_status_payload = data
                order.save()
            except Exception:
                pass

            # Reconcile Donations app if paid
            if paid:
                try:
                    from donations.models import Donation
                    from donations.services import mark_paid_and_receipt, issue_magic_link
                    from donations.emails import send_receipt_email
                    from django.urls import reverse

                    donation = (
                        Donation.objects.filter(txn_id=order_id).first() or
                        Donation.objects.filter(order_id=data.get("id") or "").first() or
                        Donation.objects.filter(txn_id=data.get("txn_id") or "").first()
                    )
                    if donation and donation.status != "SUCCESS":
                        mode = data.get("payment_method") or data.get("payment_method_type") or ""
                        mark_paid_and_receipt(donation, mode, data)
                        meta = donation.gateway_meta or {}
                        if not bool(meta.get("receipt_email_sent")):
                            try:
                                mlt = issue_magic_link(donation.donor)
                                link = request.build_absolute_uri(
                                    reverse("donations:magic_claim", kwargs={"token": mlt.token})
                                )
                                send_receipt_email(donation, magic_link_url=link)
                                meta["receipt_email_sent"] = True
                                donation.gateway_meta = meta
                                donation.save(update_fields=["gateway_meta"])
                            except Exception:
                                pass
                except Exception:
                    pass
        except HdfcError:
            # Ignore on page render; client can still try manual check
            pass

    resp = render(request, "payments/return.html", ctx)
    if order_id:
        resp.set_cookie("hdfc_last_order_id", order_id, max_age=1800, secure=True, samesite="Lax")
    if customer_id:
        resp.set_cookie("hdfc_customer_id", customer_id, max_age=1800, secure=True, samesite="Lax")
    return resp
