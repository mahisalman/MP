from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator

from .models import Withdrawal
from .forms import WithdrawalRequestForm
from .services import request_demo_withdrawal
from wallet.services import get_or_create_wallet


@login_required
def withdrawal_list_view(request):
    wallet = get_or_create_wallet(request.user)
    withdrawals = Withdrawal.objects.filter(user=request.user).order_by('-requested_at')

    paginator = Paginator(withdrawals, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'withdrawals/list.html', {
        'wallet': wallet,
        'page_obj': page_obj,
    })


@login_required
def withdrawal_request_view(request):
    wallet = get_or_create_wallet(request.user)

    if request.method == 'POST':
        form = WithdrawalRequestForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            method = form.cleaned_data['method']
            account_name = form.cleaned_data['account_name']
            account_identifier = form.cleaned_data['account_identifier']
            admin_note = form.cleaned_data.get('admin_note', '')

            try:
                wd = request_demo_withdrawal(
                    request.user,
                    amount,
                    method,
                    account_name,
                    account_identifier,
                    admin_note
                )
                messages.success(
                    request,
                    f"Simulated withdrawal #{wd.id} for {amount} DUSD submitted! Funds are locked in your demo balance awaiting admin review."
                )
                return redirect('withdrawals:list')
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))
            except Exception as e:
                messages.error(request, f"Error processing withdrawal request: {str(e)}")
    else:
        form = WithdrawalRequestForm(initial={'account_name': request.user.full_name or request.user.username})

    return render(request, 'withdrawals/request.html', {
        'form': form,
        'wallet': wallet,
    })
