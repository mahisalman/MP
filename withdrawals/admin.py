from django.contrib import admin
from .models import Withdrawal

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'method', 'status', 'processed_by', 'requested_at')
    list_filter = ('status', 'method', 'requested_at')
    search_fields = ('user__username', 'account_identifier', 'account_name')
    readonly_fields = ('requested_at', 'approved_at', 'completed_at', 'rejected_at')
