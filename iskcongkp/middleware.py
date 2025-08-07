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
