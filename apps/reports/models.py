import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class ReportType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    template_path = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'reports_report_type'
        unique_together = ['institution', 'code']
    
    def __str__(self):
        return self.name

class GeneratedReport(models.Model):
    FORMAT_CHOICES = (
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('html', 'HTML'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    report_name = models.CharField(max_length=255)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='pdf')
    parameters = models.JSONField(default=dict)
    file_path = models.CharField(max_length=500, blank=True)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'reports_generated_report'
    
    def __str__(self):
        return self.report_name

class DashboardWidget(models.Model):
    WIDGET_TYPES = (
        ('chart', 'Chart'),
        ('stats', 'Statistics'),
        ('table', 'Table'),
        ('list', 'List'),
    )
    
    CHART_TYPES = (
        ('bar', 'Bar Chart'),
        ('line', 'Line Chart'),
        ('pie', 'Pie Chart'),
        ('doughnut', 'Doughnut Chart'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    chart_type = models.CharField(max_length=20, choices=CHART_TYPES, blank=True)
    data_source = models.CharField(max_length=255)
    position = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'reports_dashboard_widget'
        ordering = ['position']
    
    def __str__(self):
        return self.name

class ReportSchedule(models.Model):
    FREQUENCY_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    format = models.CharField(max_length=10, choices=GeneratedReport.FORMAT_CHOICES, default='pdf')
    parameters = models.JSONField(default=dict)
    recipients = models.TextField(help_text="Comma-separated email addresses")
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reports_report_schedule'
    
    def __str__(self):
        return self.name