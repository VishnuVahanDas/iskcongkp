from django.conf import settings
import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse


logger = logging.getLogger(__name__)


def _should_fail_silently() -> bool:
    """Determine whether to fail silently when sending emails.

    Controlled via settings.EMAIL_FAIL_SILENTLY (default: True).
    """
    return getattr(settings, "EMAIL_FAIL_SILENTLY", True)


def send_welcome_email(*, user, request=None) -> None:
    """Send a welcome email using the HTML template.

    Sends a multi-part (text + HTML) email. Intentionally does not include
    the user's password for security reasons.
    """
    if not user or not getattr(user, "email", None):
        return

    subject = "Welcome to ISKCON Gorakhpur"
    full_name = f"{user.first_name} {user.last_name}".strip()
    context = {
        "username": full_name or user.username,
        "email": user.email,
        "login_url": None,
    }

    try:
        if request is not None:
            try:
                context["login_url"] = request.build_absolute_uri(reverse("accounts:login"))
            except Exception:
                context["login_url"] = None

        html_body = render_to_string("emails/welcome_email.html", context)

        # Provide a minimal text alternative for clients that don't render HTML
        text_body = render_to_string(
            "emails/welcome_email.txt",
            context,
        ) if template_exists("emails/welcome_email.txt") else (
            f"Hare Krishna {context['username']},\n\n"
            f"Your account has been created successfully.\n"
            f"Username: {user.username}\n"
            f"Email: {user.email}\n"
            + (f"Sign in: {context['login_url']}\n" if context.get("login_url") else "")
            + "\nYours in service,\nISKCON Gorakhpur"
        )

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@iskcongorakhpur.com")
        msg = EmailMultiAlternatives(subject, text_body, from_email, [user.email])
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=_should_fail_silently())
    except Exception:
        # Never block signup flow due to email errors; log for ops visibility
        logger.exception("Failed to send welcome email to %s", getattr(user, "email", None))


def template_exists(path: str) -> bool:
    """Best-effort check for template existence without raising errors."""
    from django.template import engines

    try:
        django_engine = engines["django"]
        django_engine.get_template(path)
        return True
    except Exception:
        return False


def send_signup_otp_email(*, email: str, username: str, code: str) -> bool:
    """Send the email OTP during signup.

    Returns True on success, False if sending fails.
    """
    if not email:
        return False
    try:
        logger.info(
            "Sending signup OTP email: to=%s subject=%s host=%s port=%s ssl=%s tls=%s",
            email,
            "Your ISKCON Gorakhpur verification code",
            getattr(settings, "EMAIL_HOST", None),
            getattr(settings, "EMAIL_PORT", None),
            getattr(settings, "EMAIL_USE_SSL", None),
            getattr(settings, "EMAIL_USE_TLS", None),
        )
        subject = "Your ISKCON Gorakhpur verification code"
        context = {"username": username, "code": code}
        html_body = render_to_string("emails/otp_email.html", context)
        text_body = f"Dear {username},\nYour verification code is: {code}\n\nHare Krishna,\nTeam ISKCON"
        from_email = getattr(settings, "EMAIL_HOST_USER", None) or getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@iskcongorakhpur.com")
        logger.info("Using from address for signup OTP: %s", from_email)
        msg = EmailMultiAlternatives(subject, text_body, from_email, [email])
        msg.attach_alternative(html_body, "text/html")
        sent_count = msg.send(fail_silently=_should_fail_silently())
        return bool(sent_count)
    except Exception:
        # Do not raise in user flow; log error for diagnosis
        logger.exception("Failed to send signup OTP email to %s", email)
        return False


def send_login_otp_email(*, email: str, username: str, code: str) -> bool:
    """Send the email OTP during login verification.

    Uses the same HTML template as signup OTP.
    """
    if not email:
        return False
    try:
        logger.info(
            "Sending login OTP email: to=%s subject=%s host=%s port=%s ssl=%s tls=%s",
            email,
            "Your ISKCON Gorakhpur login code",
            getattr(settings, "EMAIL_HOST", None),
            getattr(settings, "EMAIL_PORT", None),
            getattr(settings, "EMAIL_USE_SSL", None),
            getattr(settings, "EMAIL_USE_TLS", None),
        )
        subject = "Your ISKCON Gorakhpur login code"
        context = {"username": username, "code": code}
        html_body = render_to_string("emails/otp_email.html", context)
        text_body = f"Dear {username},\nYour login code is: {code}\n\nHare Krishna,\nTeam ISKCON"
        # Prefer authenticated SMTP user as from address for provider compatibility
        from_email = getattr(settings, "EMAIL_HOST_USER", None) or getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@iskcongorakhpur.com")
        logger.info("Using from address for login OTP: %s", from_email)
        msg = EmailMultiAlternatives(subject, text_body, from_email, [email])
        msg.attach_alternative(html_body, "text/html")
        sent_count = msg.send(fail_silently=_should_fail_silently())
        return bool(sent_count)
    except Exception:
        logger.exception("Failed to send login OTP email to %s", email)
        return False
