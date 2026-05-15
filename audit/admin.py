from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action_type', 'table_name', 'record_id', 'user', 'created_at']
    list_filter = ['action_type', 'table_name', 'created_at']
    search_fields = ['reason']
    readonly_fields = ['action_type', 'table_name', 'record_id', 'old_values', 'new_values', 'reason', 'ip_address', 'user', 'created_at']
