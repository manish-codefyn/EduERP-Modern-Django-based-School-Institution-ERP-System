# reports/admin.py
from django.contrib import admin
from django.utils.html import format_html
import json

from .models import (
    ReportType,
    GeneratedReport,
    DashboardWidget,
    ReportSchedule,
)


@admin.register(ReportType)
class ReportTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "code", "is_active")
    list_filter = ("institution", "is_active")
    search_fields = ("name", "code", "description")
    ordering = ("name",)


@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ("report_name", "institution", "report_type", "format", "generated_by", "generated_at", "file_link")
    list_filter = ("institution", "format", "generated_at")
    search_fields = ("report_name", "report_type__name", "generated_by__username")
    ordering = ("-generated_at",)

    def file_link(self, obj):
        if obj.file_path:
            return format_html('<a href="{}" target="_blank">Download</a>', obj.file_path)
        return "-"
    file_link.short_description = "File"


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "widget_type", "chart_type", "position", "is_active")
    list_filter = ("institution", "widget_type", "chart_type", "is_active")
    search_fields = ("name", "data_source")
    ordering = ("position",)


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "report_type", "frequency", "format", "is_active", "next_run", "last_run", "created_by")
    list_filter = ("institution", "frequency", "format", "is_active")
    search_fields = ("name", "report_type__name", "recipients", "created_by__username")
    ordering = ("-next_run",)

    readonly_fields = ("last_run", "next_run")

    def get_readonly_fields(self, request, obj=None):
        """Make created_by immutable after creation"""
        if obj:
            return self.readonly_fields + ("created_by",)
        return self.readonly_fields
