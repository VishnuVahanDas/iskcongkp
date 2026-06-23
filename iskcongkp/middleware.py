from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class MaintenanceModeMiddleware:
    """Redirect all requests to the maintenance page when enabled."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "MAINTENANCE_MODE", False):
            maintenance_url = reverse("maintenance")
            excluded_paths = [maintenance_url, "/admin/"]
            static_prefix = getattr(settings, "STATIC_URL", "/static/")
            media_prefix = getattr(settings, "MEDIA_URL", "/media/")
            if (
                not request.path.startswith(tuple(excluded_paths))
                and not request.path.startswith(static_prefix)
                and not request.path.startswith(media_prefix)
            ):
                return redirect(maintenance_url)
        return self.get_response(request)


class CanonicalHostMiddleware:
    """Redirect to a canonical host to keep cookies/CSRF consistent."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.canonical_host = getattr(settings, "CANONICAL_HOST", "") or ""

    def __call__(self, request):
        if self.canonical_host:
            host = request.get_host().split(":", 1)[0].lower()
            if host != self.canonical_host.lower():
                scheme = "https" if request.is_secure() else "http"
                return redirect(f"{scheme}://{self.canonical_host}{request.get_full_path()}")
        return self.get_response(request)
