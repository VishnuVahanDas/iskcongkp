from django import forms


class DonationForm(forms.Form):
    """Collect basic donor information for a donation payment."""

    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, required=False)
    amount = forms.DecimalField(decimal_places=2, max_digits=10)
    category = forms.CharField(max_length=100, required=False)
