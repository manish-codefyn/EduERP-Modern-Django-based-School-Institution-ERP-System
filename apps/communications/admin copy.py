# communications/admin.py
from django.contrib import admin
from .models import (
    Notice, NoticeAudience, SMSLog, EmailLog,
    NotificationTemplate, Broadcast
)

from django.utils.html import format_html
import json

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'institution', 'template_type', 'is_active', 'variables_preview']
    list_filter = ['template_type', 'is_active', 'institution']
    readonly_fields = ['variables_schema_preview', 'created_at', 'updated_at']
    
    def variables_preview(self, obj):
        variables = obj.get_variables_for_ui() if hasattr(obj, 'get_variables_for_ui') else obj.variables
        if isinstance(variables, dict):
            return ', '.join(variables.keys()) if variables else 'No variables'
        elif isinstance(variables, list):
            return ', '.join([var['name'] for var in variables]) if variables else 'No variables'
        return 'No variables'
    variables_preview.short_description = 'Variables'
    
    def variables_schema_preview(self, obj):
        if obj.variable_schema:
            return format_html(
                '<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">{}</pre>',
                json.dumps(obj.variable_schema, indent=2)
            )
        return 'No schema defined'
    variables_schema_preview.short_description = 'Variable Schema'

    
@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "institution", "priority", "audience", "is_published", "publish_date", "expiry_date")
    list_filter = ("priority", "audience", "is_published", "institution")
    search_fields = ("title", "content")
    date_hierarchy = "publish_date"
    autocomplete_fields = ("institution", "created_by")
    ordering = ("-publish_date",)

    fieldsets = (
        (None, {
            "fields": ("institution", "title", "content", "priority", "audience", "attachment")
        }),
        ("Publication", {
            "fields": ("is_published", "publish_date", "expiry_date")
        }),
        ("Metadata", {
            "fields": ("created_by", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(NoticeAudience)
class NoticeAudienceAdmin(admin.ModelAdmin):
    list_display = ("notice", "user", "read", "read_at")
    list_filter = ("read",)
    search_fields = ("notice__title", "user__email", "user__first_name", "user__last_name")
    autocomplete_fields = ("notice", "user")
    readonly_fields = ("read_at",)


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ("recipient_number", "institution", "status", "scheduled_for", "sent_at")
    list_filter = ("status", "institution")
    search_fields = ("recipient_number", "message")
    autocomplete_fields = ("institution",)
    readonly_fields = ("provider_response", "created_at", "updated_at")


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("recipient_email", "institution", "subject", "status", "scheduled_for", "sent_at")
    list_filter = ("status", "institution")
    search_fields = ("recipient_email", "subject", "message")
    autocomplete_fields = ("institution",)
    readonly_fields = ("provider_response", "created_at", "updated_at")



@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "audience", "channel", "status", "scheduled_for", "created_by")
    list_filter = ("audience", "channel", "status", "institution")
    search_fields = ("name", "message")
    autocomplete_fields = ("institution", "template", "created_by")
    readonly_fields = ("total_recipients", "successful", "failed", "created_at", "updated_at")
    date_hierarchy = "scheduled_for"
