from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator

from .models import RewardPlan, RewardPosition, DailyReward
from .services import create_demo_position
from .forms import AllocatePositionForm
from wallet.services import get_or_create_wallet


@login_required
def positions_list_view(request):
    positions = RewardPosition.objects.filter(user=request.user).order_by('-created_at')
    active_count = positions.filter(status='ACTIVE').count()
    completed_count = positions.filter(status='COMPLETED').count()

    paginator = Paginator(positions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'rewards/positions_list.html', {
        'page_obj': page_obj,
        'active_count': active_count,
        'completed_count': completed_count,
    })


@login_required
def allocate_position_view(request):
    wallet = get_or_create_wallet(request.user)
    plans = RewardPlan.objects.filter(is_active=True)

    if request.method == 'POST':
        form = AllocatePositionForm(request.POST)
        if form.is_valid():
            plan = form.cleaned_data['plan']
            amount = form.cleaned_data['demo_amount']

            try:
                position = create_demo_position(request.user, plan, amount)
                messages.success(
                    request,
                    f"Successfully allocated position #{position.id}! You will receive {position.daily_reward_amount} DUSD (2%) daily for 75 days in demo rewards."
                )
                return redirect('rewards:detail', position_id=position.id)
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))
            except Exception as e:
                messages.error(request, f"Error allocating position: {str(e)}")
    else:
        form = AllocatePositionForm()

    return render(request, 'rewards/allocate.html', {
        'form': form,
        'wallet': wallet,
        'plans': plans
    })


@login_required
def position_detail_view(request, position_id):
    position = get_object_or_404(RewardPosition, id=position_id, user=request.user)
    daily_rewards = DailyReward.objects.filter(position=position).order_by('-reward_date')
    
    progress_pct = position.progress_percentage

    return render(request, 'rewards/position_detail.html', {
        'position': position,
        'daily_rewards': daily_rewards,
        'progress_pct': progress_pct
    })
