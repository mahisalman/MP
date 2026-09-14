from django import forms
from decimal import Decimal
from .models import Withdrawal

class WithdrawalRequestForm(forms.ModelForm):
    class Meta:
        model = Withdrawal
        fields = ['amount', 'method', 'account_name', 'account_identifier', 'admin_note']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'e.g. 50.00',
                'step': '0.01'
            }),
            'method': forms.Select(attrs={'class': 'form-select'}),
            'account_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Demo Account Holder'
            }),
            'account_identifier': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Test Wallet Address (DEMO)'
            }),
            'admin_note': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional note for administrator'
            }),
        }
        labels = {
            'amount': 'Simulated Withdrawal Amount (DUSD)',
            'account_identifier': 'Simulated Destination Account / Address',
            'admin_note': 'Optional Note',
        }
