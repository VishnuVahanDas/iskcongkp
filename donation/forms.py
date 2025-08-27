from django import forms

class DonationForm(forms.Form):
    order_id = forms.CharField(max_length=64)
    amount = forms.DecimalField(decimal_places=2, max_digits=10)
