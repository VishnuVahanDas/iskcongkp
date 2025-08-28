from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

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


def signup_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("homepage:homepage")
    else:
        form = UserCreationForm()
    return render(request, "signup.html", {"form": form})


def signin_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("homepage:homepage")
    else:
        form = AuthenticationForm()
    return render(request, "signin.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("homepage:homepage")
