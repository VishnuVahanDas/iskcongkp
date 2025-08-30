from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    """Custom user creation form with additional fields."""

    email = forms.EmailField(required=True)
    mobile = forms.CharField(required=True, max_length=15)
    first_name = forms.CharField(required=True, max_length=150)
    last_name = forms.CharField(required=True, max_length=150)

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "mobile",
            "password1",
            "password2",
        )
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "mobile": forms.TextInput(attrs={"class": "form-control"}),
            "password1": forms.PasswordInput(attrs={"class": "form-control"}),
            "password2": forms.PasswordInput(attrs={"class": "form-control"}),
        }

    def save(self, commit=True):
        """Create user with a unique username based on names."""
        user = super().save(commit=False)
        first = self.cleaned_data.get("first_name", "").strip().lower()
        last = self.cleaned_data.get("last_name", "").strip().lower()
        base_username = f"{first}.{last}"
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user.username = username
        if commit:
            user.save()
            self.save_m2m()
        return user


class SignInForm(AuthenticationForm):
    """Authentication form with Bootstrap styling."""

    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "required": True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "required": True})
    )

