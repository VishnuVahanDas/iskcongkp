from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class SignUpStartForm(forms.Form):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))
    mobile = forms.CharField(label="Phone", max_length=15, widget=forms.TextInput(attrs={"class": "form-control"}))

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_mobile(self):
        mobile = self.cleaned_data["mobile"].strip()
        # Basic normalization: remove spaces
        mobile_norm = "".join(ch for ch in mobile if ch.isdigit() or ch in ["+","-"])
        # Username will be set to customer_id; avoid conflict with existing usernames
        if User.objects.filter(username=mobile_norm).exists():
            raise ValidationError("This phone is already registered.")
        return mobile_norm


class SignUpVerifyForm(forms.Form):
    otp = forms.CharField(label="OTP", max_length=6, widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "one-time-code"}))

