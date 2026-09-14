from django import forms
from decimal import Decimal
from .models import RewardPlan

class AllocatePositionForm(forms.Form):
    plan = forms.ModelChoiceField(
        queryset=RewardPlan.objects.filter(is_active=True),
        empty_label=None,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    demo_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('10.00'),
        max_value=Decimal('10000.00'),
        label="Simulated Allocation Amount (DUSD)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. 100.00',
            'step': '1.00'
        })
    )
