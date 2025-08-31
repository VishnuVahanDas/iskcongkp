from django.shortcuts import render, redirect
import logging
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required

from iskcongkp.forms import SignInForm
from .forms import SignUpStartForm, SignUpVerifyForm
from .models import Customer
from .emails import send_welcome_email, send_signup_otp_email
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import random


OTP_SESSION_KEY = "signup_otp"
logger = logging.getLogger(__name__)


def _generate_customer_id() -> str:
    base = f"C{uuid.uuid4().hex[:10].upper()}"
    while Customer.objects.filter(customer_id=base).exists() or User.objects.filter(username=base).exists():
        base = f"C{uuid.uuid4().hex[:10].upper()}"
    return base


def signup_view(request):
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
                request.session[OTP_SESSION_KEY] = otp_payload
                request.session.modified = True

                # Send OTP email
                display_name = f"{data['first_name']} {data.get('last_name','')}".strip() or data["email"]
                sent = send_signup_otp_email(email=data["email"], username=display_name, code=code)

                if sent:
                    verify_form = SignUpVerifyForm()
                    return render(
                        request,
                        "signup.html",
                        {"start_form": start_form, "verify_form": verify_form, "otp_sent": True},
                    )
                else:
                    # Surface error to user instead of silently proceeding
                    start_form.add_error(None, "We could not send the OTP email. Please try again in a minute or contact support.")
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
    start_form = SignUpStartForm(initial=otp_state or None)
    context = {"start_form": start_form}
    if otp_state:
        context["verify_form"] = SignUpVerifyForm()
        context["otp_sent"] = True
    return render(request, "signup.html", context)


def signin_view(request):
    if request.method == "POST":
        form = SignInForm(request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("homepage:homepage")
    else:
        form = SignInForm()
    return render(request, "signin.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("homepage:homepage")
