from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Wallet, WalletTransaction
from .services import get_or_create_wallet, create_demo_deposit
from .forms import DemoDepositForm


@login_required
def wallet_detail_view(request):
    wallet = get_or_create_wallet(request.user)
    transactions_list = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')
    
    paginator = Paginator(transactions_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'wallet/detail.html', {
        'wallet': wallet,
        'page_obj': page_obj,
    })


@login_required
def demo_deposit_view(request):
    if request.method == 'POST':
        form = DemoDepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            note = form.cleaned_data.get('note', '')
            create_demo_deposit(request.user, amount, note)
            messages.success(request, f"Successfully added {amount} DUSD to your simulated demo balance!")
            return redirect('wallet:detail')
    else:
        form = DemoDepositForm()

    return render(request, 'wallet/deposit.html', {
        'form': form
    })
