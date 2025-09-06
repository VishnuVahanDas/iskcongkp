from django.urls import path
from . import views
app_name = "payments"
urlpatterns = [
    path("test", views.hdfc_test_page_view, name="hdfc_test"),
    path("my", views.my_payments_view, name="my_payments"),
    path("create-session", views.hdfc_create_session_view, name="hdfc_create_session"),
    path("status/<str:order_id>", views.hdfc_order_status_view, name="hdfc_order_status"),
    path("return", views.hdfc_return_view, name="hdfc_return"),  # https://.../payments/return
    # Webhook alias to match configured URL https://<domain>/payments/webhook
    path("webhook", views.hdfc_webhook_alias, name="hdfc_webhook"),
]
