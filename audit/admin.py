from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'action', 'user', 'admin_user', 'entity_type', 'entity_id', 'ip_address')
    list_filter = ('action', 'entity_type', 'created_at')
    search_fields = ('user__username', 'admin_user__username', 'description', 'entity_id')
    readonly_fields = ('created_at', 'user', 'admin_user', 'action', 'entity_type', 'entity_id', 'description', 'ip_address', 'user_agent')
