import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings


class Notice(models.Model):
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    AUDIENCE_CHOICES = (
        ('all', 'All'),
        ('students', 'Students'),
        ('parents', 'Parents'),
        ('teachers', 'Teachers'),
        ('staff', 'Staff'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='all')
    is_published = models.BooleanField(default=False)
    publish_date = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    attachment = models.FileField(upload_to='notices/', blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communications_notice'
        ordering = ['-publish_date', '-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.is_published and not self.publish_date:
            self.publish_date = timezone.now()
        super().save(*args, **kwargs)

class NoticeAudience(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notice = models.ForeignKey(Notice, on_delete=models.CASCADE, related_name='audience_details')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'communications_notice_audience'
        unique_together = ['notice', 'user']
    
    def __str__(self):
        return f"{self.notice.title} - {self.user}"

class SMSLog(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    recipient_number = models.CharField(max_length=20)
    message = models.TextField()
    template_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_response = models.JSONField(default=dict)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communications_sms_log'
    
    def __str__(self):
        return f"SMS to {self.recipient_number} - {self.status}"

class EmailLog(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    template_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_response = models.JSONField(default=dict)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communications_email_log'
    
    def __str__(self):
        return f"Email to {self.recipient_email} - {self.status}"

class NotificationTemplate(models.Model):
    TYPE_CHOICES = (
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('push', 'Push Notification'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    subject = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    variables = models.JSONField(default=dict, help_text="Available template variables")
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communications_notification_template'
        unique_together = ['institution', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"

class Broadcast(models.Model):
    AUDIENCE_CHOICES = (
        ('all', 'All'),
        ('students', 'Students'),
        ('parents', 'Parents'),
        ('teachers', 'Teachers'),
        ('staff', 'Staff'),
        ('custom', 'Custom'),
    )
    
    CHANNEL_CHOICES = (
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('both', 'Both'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='all')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='both')
    message = models.TextField()
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=(
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ), default='draft')
    total_recipients = models.IntegerField(default=0)
    successful = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    
    created_by = models.ForeignKey('users.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communications_broadcast'
    
    def __str__(self):
        return self.name