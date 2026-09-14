from django import forms
from decimal import Decimal

class DemoDepositForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('1.00'),
        max_value=Decimal('100000.00'),
        label="Simulated Deposit Amount (DUSD)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. 500.00',
            'step': '0.01'
        })
    )
    note = forms.CharField(
        required=False,
        max_length=200,
        label="Simulation Note",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Test credit for simulation'
        })
    )
