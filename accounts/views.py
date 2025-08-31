from django.shortcuts import render, redirect
import logging
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache

from iskcongkp.forms import SignInForm
from .forms import SignUpStartForm, SignUpVerifyForm, SignInStartForm, SignInVerifyForm
from .models import Customer
from .emails import send_welcome_email, send_signup_otp_email, send_login_otp_email
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import random


OTP_SESSION_KEY = "signup_otp"
LOGIN_OTP_SESSION_KEY = "login_otp"
logger = logging.getLogger(__name__)


def _generate_customer_id() -> str:
    base = f"C{uuid.uuid4().hex[:10].upper()}"
    while Customer.objects.filter(customer_id=base).exists() or User.objects.filter(username=base).exists():
        base = f"C{uuid.uuid4().hex[:10].upper()}"
    return base


@ensure_csrf_cookie
@never_cache
def signup_view(request):
    # Allow manual reset via query or form action
    if request.GET.get("reset") == "1" or request.POST.get("action") == "reset_otp":
        try:
            if request.session.get(OTP_SESSION_KEY):
                del request.session[OTP_SESSION_KEY]
                request.session.modified = True
        except Exception:
            pass

    otp_state = request.session.get(OTP_SESSION_KEY)

    if request.method == "POST":
        action = request.POST.get("action") or "send_otp"

        if action == "send_otp":
            start_form = SignUpStartForm(request.POST)
            if start_form.is_valid():
                data = start_form.cleaned_data
                code = f"{random.randint(100000, 999999)}"
                logger.info(
                    "Signup OTP generated for email=%s phone=%s first=%s last=%s",
                    data.get("email"),
                    data.get("mobile"),
                    data.get("first_name"),
                    data.get("last_name", ""),
                )
                otp_payload = {
                    "first_name": data["first_name"],
                    "last_name": data.get("last_name", ""),
                    "email": data["email"],
                    "mobile": data["mobile"],
                    "code": code,
                    "created_at": timezone.now().isoformat(),
                }

                # Send OTP email first; only persist state if send succeeded
                display_name = f"{data['first_name']} {data.get('last_name','')}".strip() or data["email"]
                sent = send_signup_otp_email(email=data["email"], username=display_name, code=code)

                if sent:
                    request.session[OTP_SESSION_KEY] = otp_payload
                    request.session.modified = True
                    verify_form = SignUpVerifyForm()
                    return render(
                        request,
                        "signup.html",
                        {"start_form": start_form, "verify_form": verify_form, "otp_sent": True},
                    )
                else:
                    # Surface error to user instead of silently proceeding
                    start_form.add_error(None, "We could not send the OTP email. Please try again in a minute or contact support.")
                    # Ensure any stale OTP state is cleared to avoid stuck verify step
                    try:
                        if request.session.get(OTP_SESSION_KEY):
                            del request.session[OTP_SESSION_KEY]
                            request.session.modified = True
                    except Exception:
                        pass
                    return render(request, "signup.html", {"start_form": start_form, "otp_sent": False})
            else:
                return render(request, "signup.html", {"start_form": start_form, "otp_sent": False})

        elif action == "verify_otp":
            verify_form = SignUpVerifyForm(request.POST)
            if not otp_state:
                # No OTP in session
                start_form = SignUpStartForm()
                verify_form.add_error(None, "Session expired. Please start again.")
                return render(request, "signup.html", {"start_form": start_form, "verify_form": verify_form, "otp_sent": False})

            if verify_form.is_valid():
                if verify_form.cleaned_data["otp"] != otp_state.get("code"):
                    # Wrong OTP
                    start_form = SignUpStartForm(initial={
                        "first_name": otp_state.get("first_name", ""),
                        "last_name": otp_state.get("last_name", ""),
                        "email": otp_state.get("email", ""),
                        "mobile": otp_state.get("mobile", ""),
                    })
                    verify_form.add_error("otp", "Invalid code. Please try again.")
                    return render(request, "signup.html", {"start_form": start_form, "verify_form": verify_form, "otp_sent": True})

                # Create user and customer
                first_name = otp_state["first_name"].strip()
                last_name = otp_state.get("last_name", "").strip()
                email = otp_state["email"].strip().lower()
                mobile = otp_state["mobile"].strip()

                # Set username == customer_id (requirement), and also store phone on customer
                customer_id = _generate_customer_id()

                # Generate a secure random password; user will be logged in immediately
                random_password = uuid.uuid4().hex
                user = User.objects.create_user(
                    username=customer_id,
                    email=email,
                    password=random_password,
                    first_name=first_name,
                    last_name=last_name,
                )
                Customer.objects.create(
                    user=user,
                    customer_id=customer_id,
                    phone=mobile,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                )

                # Cleanup session OTP
                try:
                    del request.session[OTP_SESSION_KEY]
                except Exception:
                    pass

                login(request, user)
                send_welcome_email(user=user, request=request)
                return redirect("homepage:homepage")

            # Invalid verify form
            start_form = SignUpStartForm(initial=otp_state or {})
            return render(request, "signup.html", {"start_form": start_form, "verify_form": verify_form, "otp_sent": True})

    # GET or fallthrough
    # Expire stale OTP state after 10 minutes
    from datetime import datetime, timedelta
    from django.utils.dateparse import parse_datetime
    is_valid_otp_state = False
    if otp_state:
        try:
            created_dt = parse_datetime(otp_state.get("created_at"))
            if created_dt and timezone.now() - created_dt <= timedelta(minutes=10):
                is_valid_otp_state = True
            else:
                # Expire old state
                del request.session[OTP_SESSION_KEY]
                request.session.modified = True
                otp_state = None
        except Exception:
            otp_state = None

    start_form = SignUpStartForm(initial=otp_state or None)
    context = {"start_form": start_form}
    if is_valid_otp_state:
        context["verify_form"] = SignUpVerifyForm()
        context["otp_sent"] = True
    return render(request, "signup.html", context)


@ensure_csrf_cookie
@never_cache
def signin_view(request):
    # Allow resetting login flow
    if request.GET.get("reset") == "1" or request.POST.get("action") == "reset_otp":
        try:
            if request.session.get(LOGIN_OTP_SESSION_KEY):
                del request.session[LOGIN_OTP_SESSION_KEY]
                request.session.modified = True
        except Exception:
            pass

    state = request.session.get(LOGIN_OTP_SESSION_KEY)
    action = request.POST.get("action") or "send_otp"

    if request.method == "POST" and action == "send_otp":
        start_form = SignInStartForm(request.POST)
        if start_form.is_valid():
            identifier = start_form.cleaned_data["identifier"].strip()

            # Determine target user and destination email
            user = None
            target_email = None
            display_name = None

            # Email path
            try:
                from django.core.validators import validate_email as _validate_email
                _validate_email(identifier)
                user = User.objects.filter(email__iexact=identifier).first()
                if not user:
                    from .models import Customer
                    cust = Customer.objects.filter(email__iexact=identifier).select_related("user").first()
                    if cust:
                        user = cust.user
                if user:
                    target_email = user.email
            except Exception:
                # Phone path
                from .models import Customer
                phone_norm = "".join(ch for ch in identifier if ch.isdigit() or ch in ["+","-"])
                cust = Customer.objects.filter(phone=phone_norm).select_related("user").first()
                if cust:
                    user = cust.user
                    target_email = cust.email or getattr(user, "email", None)

            if not user or not target_email:
                start_form.add_error("identifier", "No account found for this email or phone.")
                return render(request, "signin.html", {"start_form": start_form, "otp_sent": False})

            code = f"{random.randint(100000, 999999)}"
            display_name = f"{user.first_name} {user.last_name}".strip() or user.username
            sent = send_login_otp_email(email=target_email, username=display_name, code=code)
            if sent:
                payload = {
                    "user_id": user.id,
                    "email": target_email,
                    "code": code,
                    "created_at": timezone.now().isoformat(),
                }
                request.session[LOGIN_OTP_SESSION_KEY] = payload
                request.session.modified = True
                verify_form = SignInVerifyForm()
                return render(request, "signin.html", {"start_form": start_form, "verify_form": verify_form, "otp_sent": True})
            else:
                start_form.add_error(None, "Failed to send the OTP email. Please try again shortly.")
                try:
                    if request.session.get(LOGIN_OTP_SESSION_KEY):
                        del request.session[LOGIN_OTP_SESSION_KEY]
                        request.session.modified = True
                except Exception:
                    pass
                return render(request, "signin.html", {"start_form": start_form, "otp_sent": False})
        else:
            return render(request, "signin.html", {"start_form": start_form, "otp_sent": False})

    elif request.method == "POST" and action == "verify_otp":
        verify_form = SignInVerifyForm(request.POST)
        if not state:
            start_form = SignInStartForm()
            verify_form.add_error(None, "Session expired. Please start again.")
            return render(request, "signin.html", {"start_form": start_form, "verify_form": verify_form, "otp_sent": False})

        if verify_form.is_valid():
            if verify_form.cleaned_data["otp"] != state.get("code"):
                start_form = SignInStartForm()
                verify_form.add_error("otp", "Invalid code. Please try again.")
                return render(request, "signin.html", {"start_form": start_form, "verify_form": verify_form, "otp_sent": True})

            # Success: log in and redirect
            try:
                user = User.objects.get(id=state.get("user_id"))
            except User.DoesNotExist:
                start_form = SignInStartForm()
                verify_form.add_error(None, "Account not found. Please try again.")
                return render(request, "signin.html", {"start_form": start_form, "verify_form": verify_form, "otp_sent": False})

            try:
                del request.session[LOGIN_OTP_SESSION_KEY]
            except Exception:
                pass
            login(request, user)
            return redirect("homepage:homepage")

        # invalid verify form
        start_form = SignInStartForm()
        return render(request, "signin.html", {"start_form": start_form, "verify_form": verify_form, "otp_sent": True})

    # GET
    # Expire stale login OTP after 10 minutes
    from datetime import timedelta
    from django.utils.dateparse import parse_datetime
    is_valid_state = False
    if state:
        try:
            created_dt = parse_datetime(state.get("created_at"))
            if created_dt and timezone.now() - created_dt <= timedelta(minutes=10):
                is_valid_state = True
            else:
                del request.session[LOGIN_OTP_SESSION_KEY]
                request.session.modified = True
                state = None
        except Exception:
            state = None

    start_form = SignInStartForm()
    context = {"start_form": start_form}
    if is_valid_state:
        context["verify_form"] = SignInVerifyForm()
        context["otp_sent"] = True
    return render(request, "signin.html", context)


def logout_view(request):
    logout(request)
    return redirect("homepage:homepage")
