from django.urls import path
from . import views

urlpatterns = [
    path("create-session", views.hdfc_create_session_view, name="hdfc_create_session"),
    path("status/<str:order_id>", views.hdfc_order_status_view, name="hdfc_order_status"),
    path("return", views.hdfc_return_view, name="hdfc_return"),
    # Optional: this is the path you set in HDFC_RETURN_URL (must be HTTPS, no query params).
    # You can implement a simple thank-you page here if you like.
]
