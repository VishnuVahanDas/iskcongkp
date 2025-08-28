"""
URL configuration for iskconsnc project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path as url
from django.conf.urls.static import static
from django.views.static import serve


from .views import  contact_view, privacy_view , terms_view, maintenance_view, signup_view, signin_view, logout_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("homepage.urls")),
    path("donation/", include("donation.urls")),
    path("who-we-are/", include("who_we_are.urls")),
    path("services/", include("services.urls")),
    path("festivals/", include("festivals.urls")),
    path("contact", contact_view, name="contact"),
    path("terms", terms_view, name="terms"),
    path("privacy-policy", privacy_view, name="privacy-policy"),
    path("maintenance/", maintenance_view, name="maintenance"),
    path("signup/", signup_view, name="signup"),
    path("login/", signin_view, name="login"),
    path("logout/", logout_view, name="logout"),
    url(r'^assets/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT})

]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers
handler404 = 'iskcongkp.views.error_404_view'

