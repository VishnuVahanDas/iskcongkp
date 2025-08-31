from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.template import engines
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

FROM = getattr(settings, "DONATIONS_FROM_EMAIL", None) or getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@iskcongorakhpur.com")
FAIL_SILENTLY = getattr(settings, "EMAIL_FAIL_SILENTLY", True)


def _template_exists(path: str) -> bool:
    try:
        engines["django"].get_template(path)
        return True
    except Exception:
        return False


def send_receipt_email(donation, magic_link_url=None):
    ctx = {"donation": donation, "donor": donation.donor, "magic_link_url": magic_link_url}
    subject = f"Receipt: {donation.issued_receipt_no} (ISKCON Gorakhpur)"
    text = render_to_string("emails/email_receipt.txt", ctx)
    msg = EmailMultiAlternatives(subject, text, FROM, [donation.donor.email])
    if _template_exists("emails/email_receipt.html"):
        try:
            html = render_to_string("emails/email_receipt.html", ctx)
            msg.attach_alternative(html, "text/html")
        except Exception:
            logger.exception("Failed to render HTML receipt template; sending text-only")
    msg.send(fail_silently=FAIL_SILENTLY)


def send_magic_link_email(donor, link_url):
    ctx = {"donor": donor, "magic_link_url": link_url}
    subject = "Your secure sign-in link (ISKCON Gorakhpur)"
    text = render_to_string("emails/email_magic_link.txt", ctx)
    msg = EmailMultiAlternatives(subject, text, FROM, [donor.email])
    if _template_exists("emails/email_magic_link.html"):
        try:
            html = render_to_string("emails/email_magic_link.html", ctx)
            msg.attach_alternative(html, "text/html")
        except Exception:
            logger.exception("Failed to render HTML magic link template; sending text-only")
    msg.send(fail_silently=FAIL_SILENTLY)


def send_otp_email(donor, code):
    ctx = {"donor": donor, "otp": code}
    subject = "Your one-time verification code (ISKCON Gorakhpur)"
    text = render_to_string("emails/email_otp.txt", ctx)
    msg = EmailMultiAlternatives(subject, text, FROM, [donor.email])
    if _template_exists("emails/email_otp.html"):
        try:
            html = render_to_string("emails/email_otp.html", ctx)
            msg.attach_alternative(html, "text/html")
        except Exception:
            logger.exception("Failed to render HTML OTP template; sending text-only")
    msg.send(fail_silently=FAIL_SILENTLY)
