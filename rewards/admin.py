from django.contrib import admin
from .models import RewardPlan, RewardPosition, DailyReward

@admin.register(RewardPlan)
class RewardPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'daily_rate', 'duration_days', 'minimum_demo_amount', 'maximum_demo_amount', 'is_active')
    list_filter = ('is_active',)

@admin.register(RewardPosition)
class RewardPositionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'reward_plan', 'demo_amount', 'daily_rate', 'duration_days', 'reward_earned', 'total_reward_limit', 'status', 'created_at')
    list_filter = ('status', 'reward_plan', 'created_at')
    search_fields = ('user__username', 'user__email')

@admin.register(DailyReward)
class DailyRewardAdmin(admin.ModelAdmin):
    list_display = ('id', 'position', 'user', 'reward_date', 'reward_rate', 'reward_amount', 'status', 'created_at')
    list_filter = ('reward_date', 'status')
    search_fields = ('user__username',)
