from django.contrib import admin
from django.utils.html import format_html
from .models import (
    NotificationTemplate, TemplateRenderer, Notice, NoticeAudience, 
    SMSLog, EmailLog, Broadcast, PushNotification
)
import json

# ---------------- NotificationTemplate Admin ----------------
@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'institution', 'template_type', 'is_active', 'variable_count', 'variables_preview']
    list_filter = ['template_type', 'is_active', 'institution']
    search_fields = ['name', 'subject', 'content']
    readonly_fields = ['created_at', 'updated_at', 'variable_count', 'variables_schema_preview']
    
    def variables_preview(self, obj):
        if obj.variables:
            return ', '.join([f"{k} ({v})" for k, v in obj.variables.items()])
        return 'No variables'
    variables_preview.short_description = 'Variables'
    
    def variables_schema_preview(self, obj):
        if obj.variables:
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">{}</pre>',
                               json.dumps(obj.variables, indent=2))
        return 'No schema defined'
    variables_schema_preview.short_description = 'Variable Schema'

# ---------------- Notice Admin ----------------
@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ['title', 'institution', 'priority', 'audience', 'is_published', 'publish_date', 'expiry_date']
    list_filter = ['priority', 'audience', 'is_published', 'institution']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'publish_date'

# ---------------- NoticeAudience Admin ----------------
@admin.register(NoticeAudience)
class NoticeAudienceAdmin(admin.ModelAdmin):
    list_display = ['notice', 'user', 'read', 'read_at', 'delivered', 'delivered_at']
    list_filter = ['read', 'delivered']
    search_fields = ['notice__title', 'user__username', 'user__email']

# ---------------- SMSLog Admin ----------------
@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ['recipient_number', 'institution', 'status', 'scheduled_for', 'sent_at']
    list_filter = ['status', 'institution']
    search_fields = ['recipient_number', 'message']
    readonly_fields = ['created_at', 'updated_at']

# ---------------- EmailLog Admin ----------------
@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient_email', 'subject', 'institution', 'status', 'scheduled_for', 'sent_at']
    list_filter = ['status', 'institution']
    search_fields = ['recipient_email', 'subject', 'message']
    readonly_fields = ['created_at', 'updated_at']

# ---------------- Broadcast Admin ----------------
@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ['name', 'institution', 'audience', 'channel', 'status', 'scheduled_for', 'total_recipients', 'successful', 'failed', 'progress']
    list_filter = ['status', 'audience', 'channel', 'institution']
    search_fields = ['name', 'message']
    readonly_fields = ['created_at', 'updated_at', 'total_recipients', 'successful', 'failed']
    
    def progress(self, obj):
        return f"{obj.progress_percentage}%"
    progress.short_description = 'Progress'

# ---------------- PushNotification Admin ----------------
@admin.register(PushNotification)
class PushNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'institution', 'priority', 'audience', 'status', 'scheduled_for', 'total_recipients', 'successful', 'failed']
    list_filter = ['priority', 'audience', 'status', 'institution']
    search_fields = ['title', 'message']
    readonly_fields = ['created_at', 'updated_at']

