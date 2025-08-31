from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, FieldError
from django.core.validators import validate_email


class SignUpForm(forms.ModelForm):
    """Signup without asking for password; generates one automatically."""

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
        )
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "mobile": forms.TextInput(attrs={"class": "form-control"}),
        }

    def save(self, commit=True):
        """Create user, set unique username, and generate a random password."""
        user = super().save(commit=False)
        first = self.cleaned_data.get("first_name", "").strip().lower()
        last = self.cleaned_data.get("last_name", "").strip().lower()
        base_username = f"{first}.{last}".strip(".") or first or last or "user"
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user.username = username

        # Generate a readable, strong password
        random_password = User.objects.make_random_password()
        user.set_password(random_password)

        if commit:
            user.save()
            # No M2M on auth.User default, but call for completeness if extended
            try:
                self.save_m2m()
            except Exception:
                pass
        return user


class SignInForm(forms.Form):
    """Authenticate using either email or phone identifier."""

    identifier = forms.CharField(
        label="Email or phone",
        widget=forms.TextInput(attrs={"class": "form-control", "required": True}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "required": True})
    )

    user_cache = None

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get("identifier")
        password = cleaned_data.get("password")
        user = None

        if identifier and password:
            try:
                validate_email(identifier)
                user = User.objects.filter(email__iexact=identifier).first()
            except ValidationError:
                try:
                    user = User.objects.filter(mobile=identifier).first()
                except FieldError:
                    user = None

            if not user or not user.check_password(password):
                raise forms.ValidationError("Invalid credentials")

            self.user_cache = user

        return cleaned_data

    def get_user(self):
        return self.user_cache
