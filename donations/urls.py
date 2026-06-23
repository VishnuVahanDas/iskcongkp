from django.urls import path

from . import views, webhook
from .views import (
    NityaSevaInitiateView,
    NityaSevaSuccessView,
    NityaSevaFailureView,
    NityaSevaWebhookView,
    NityaSevaStatusView,
    NityaSevaClientConfirmView,
)

app_name = "donations"
urlpatterns = [
    path("donate/", views.donate_form, name="donate_form"),
    path("donate/start", views.donate_choose, name="donate_choose"),
    path("donate/checkout", views.donate_checkout, name="donate_checkout"),
    path("donate/thank-you", views.thank_you, name="thank_you"),
    path("donate/easebuzz/response", views.easebuzz_response, name="easebuzz_response"),

    # magic link + otp
    path("auth/magic/request", views.magic_request, name="magic_request"),
    path("auth/magic/<str:token>", views.magic_claim, name="magic_claim"),
    path("auth/otp/request", views.otp_request, name="otp_request"),
    path("auth/otp/verify", views.otp_verify, name="otp_verify"),

    # donor claim + dashboard (hybrid flow)
    path("donor/claim", views.donor_claim_redirect, name="donor_claim"),
    path("donor/dashboard", views.donor_dashboard, name="donor_dashboard"),

    # webhook lives here
    path("payments/webhook", webhook.payment_webhook, name="payment_webhook"),
    path("payments/webhook/", webhook.payment_webhook),
    
    path("", views.shastra_daan, name="shastra_daan"),
    path("shastra-daan", views.shastra_daan, name="shastra_daan"),
    path("temple-seva", views.temple_seva, name="temple_seva"),
    path("annadana-seva", views.annadana_seva, name="annadana_seva"),
    path("nitya-seva", views.nitya_seva, name="nitya_seva"),
    path("janmashtami-seva", views.janmashtami_seva, name="janmashtami_seva"),
    path("tula-daan-utsav", views.tula_daan, name="tula_daan"),
    path("donate-a-brick", views.donate_brick, name="donate_brick"),

    # ── UPI AutoPay — Nitya Seva ONLY ──────────────────────────────────────
    path("nitya-seva/initiate/",
         NityaSevaInitiateView.as_view(),  name="nitya_seva_initiate"),
    path("nitya-seva/success/",
         NityaSevaSuccessView.as_view(),   name="nitya_seva_success"),
    path("nitya-seva/failure/",
         NityaSevaFailureView.as_view(),   name="nitya_seva_failure"),
    path("nitya-seva/webhook/",
         NityaSevaWebhookView.as_view(),   name="nitya_seva_webhook"),
    path("nitya-seva/status/<str:txnid>/",
         NityaSevaStatusView.as_view(),    name="nitya_seva_status"),
    path("nitya-seva/client-confirm/",
         NityaSevaClientConfirmView.as_view(), name="nitya_seva_client_confirm"),
]
