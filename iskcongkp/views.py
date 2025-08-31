from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache
from django.contrib.auth import login, logout

from .forms import SignUpForm

def contact_view(request):
    return render(request, 'contact.html')

def terms_view(request):
    return render(request, 'terms.html')

def privacy_view(request):
    return render(request, 'privacy.html')

def maintenance_view(request):
    return render(request, 'maintenance.html')

def error_404_view(request, exception):
    # we add the path to the 404.html file
    # here. The name of our HTML file is 404.html
    return render(request, '404.html', status=404)


@ensure_csrf_cookie
@never_cache
def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("homepage:homepage")
    else:
        form = SignUpForm()
    return render(request, "signup.html", {"form": form})


@ensure_csrf_cookie
@never_cache
def signin_view(request):
    # Delegate to accounts OTP login to avoid duplication
    from accounts.views import signin_view as accounts_signin
    return accounts_signin(request)


def csrf_failure(request, reason="", template_name="csrf_failure.html"):
    """Custom CSRF failure handler to show a helpful message.

    Note: OTP and sessions require cookies. If cookies are disabled, sign-in/up cannot proceed.
    """
    context = {
        "reason": reason,
    }
    return render(request, template_name, context, status=403)


def logout_view(request):
    logout(request)
    return redirect("homepage:homepage")
