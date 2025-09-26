import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.core.validators import ValidationError
import json
import re
from .utils import TemplateRenderer

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
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
    
    def clean(self):
        """Validate template variables and content"""
        super().clean()
        self.validate_variables()
        self.validate_template_content()
    
    def validate_variables(self):
        """Validate variables format and naming"""
        if not isinstance(self.variables, dict):
            raise ValidationError({'variables': 'Variables must be a JSON object'})
        
        # Validate variable names (alphanumeric and underscores only)
        for key in self.variables.keys():
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                raise ValidationError({
                    'variables': f'Variable "{key}" must contain only letters, numbers, and underscores'
                })
    
    def validate_template_content(self):
        """Validate that variables in content match defined variables"""
        content_variables = TemplateRenderer.extract_variables(self.content)
        subject_variables = TemplateRenderer.extract_variables(self.subject) if self.subject else []
        
        all_used_variables = set(content_variables + subject_variables)
        defined_variables = set(self.variables.keys())
        
        undefined_variables = all_used_variables - defined_variables
        if undefined_variables:
            raise ValidationError({
                'content': f'Undefined variables used in template: {", ".join(undefined_variables)}'
            })
    
    def get_variables_display(self):
        """Return formatted variables for display"""
        if not self.variables:
            return "No variables defined"
        
        return ", ".join([f"{key} ({desc})" for key, desc in self.variables.items()])
    
    def render_template(self, context_variables):
        """Render the template with provided variables"""
        # Validate all required variables are provided
        missing_vars = TemplateRenderer.validate_variables(self.content, context_variables)
        if missing_vars:
            raise ValueError(f"Missing template variables: {', '.join(missing_vars)}")
        
        rendered_content = TemplateRenderer.render_template(self.content, context_variables)
        rendered_subject = TemplateRenderer.render_template(self.subject, context_variables) if self.subject else ""
        
        return {
            'subject': rendered_subject,
            'content': rendered_content
        }
    
    def preview(self, sample_variables=None):
        """Generate a preview of the template with sample variables"""
        if sample_variables is None:
            sample_variables = {key: f"[{key.upper()}]" for key in self.variables.keys()}
        
        try:
            return self.render_template(sample_variables)
        except ValueError as e:
            return {'error': str(e)}
    
    @property
    def variable_count(self):
        """Return the number of variables defined"""
        return len(self.variables) if self.variables else 0


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
        ('custom', 'Custom'),
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
    
    # Template integration
    template = models.ForeignKey(
        NotificationTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Optional template to use for this notice"
    )
    template_variables = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Variables to use with the template"
    )
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communications_notice'
        ordering = ['-publish_date', '-created_at']
        indexes = [
            models.Index(fields=['institution', 'is_published', 'publish_date']),
            models.Index(fields=['publish_date', 'expiry_date']),
        ]
    
    def __str__(self):
        return self.title
    
    def clean(self):
        """Validate notice data"""
        if self.expiry_date and self.publish_date and self.expiry_date <= self.publish_date:
            raise ValidationError('Expiry date must be after publish date')
        
        if self.template and self.template.template_type != 'email':
            raise ValidationError('Notice template must be of type email')
    
    def save(self, *args, **kwargs):
        """Auto-set publish date when publishing"""
        if self.is_published and not self.publish_date:
            self.publish_date = timezone.now()
        
        # Render template content if template is used
        if self.template and self.template_variables:
            try:
                rendered = self.template.render_template(self.template_variables)
                self.content = rendered['content']
                if not self.title and rendered['subject']:
                    self.title = rendered['subject']
            except ValueError as e:
                # If template rendering fails, keep original content
                pass
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if the notice has expired"""
        if self.expiry_date:
            return timezone.now() > self.expiry_date
        return False
    
    @property
    def is_active(self):
        """Check if notice is currently active"""
        if not self.is_published:
            return False
        if self.publish_date and timezone.now() < self.publish_date:
            return False
        if self.is_expired:
            return False
        return True
    
    def get_audience_display(self):
        """Get formatted audience display"""
        return dict(self.AUDIENCE_CHOICES).get(self.audience, self.audience)


class NoticeAudience(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notice = models.ForeignKey(Notice, on_delete=models.CASCADE, related_name='audience_details')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Additional tracking fields
    delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    notification_sent = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'communications_notice_audience'
        unique_together = ['notice', 'user']
        indexes = [
            models.Index(fields=['notice', 'read']),
            models.Index(fields=['user', 'read']),
        ]
    
    def __str__(self):
        return f"{self.notice.title} - {self.user}"
    
    def mark_as_read(self):
        """Mark notice as read for this user"""
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.save()
    
    def mark_as_delivered(self):
        """Mark notice as delivered to this user"""
        if not self.delivered:
            self.delivered = True
            self.delivered_at = timezone.now()
            self.save()


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
    template = models.ForeignKey(
        NotificationTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    template_variables = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_response = models.JSONField(default=dict)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Additional tracking fields
    cost = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    message_id = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communications_sms_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['institution', 'status']),
            models.Index(fields=['recipient_number', 'created_at']),
        ]
    
    def __str__(self):
        return f"SMS to {self.recipient_number} - {self.status}"
    
    def save(self, *args, **kwargs):
        """Auto-render template message if template is used"""
        if self.template and self.template_variables and self.template.template_type == 'sms':
            try:
                rendered = self.template.render_template(self.template_variables)
                self.message = rendered['content']
            except ValueError as e:
                # If template rendering fails, keep original message
                pass
        
        super().save(*args, **kwargs)


class EmailLog(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    template = models.ForeignKey(
        NotificationTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    template_variables = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_response = models.JSONField(default=dict)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Additional tracking fields
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    message_id = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communications_email_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['institution', 'status']),
            models.Index(fields=['recipient_email', 'created_at']),
        ]
    
    def __str__(self):
        return f"Email to {self.recipient_email} - {self.status}"
    
    def save(self, *args, **kwargs):
        """Auto-render template content if template is used"""
        if self.template and self.template_variables and self.template.template_type == 'email':
            try:
                rendered = self.template.render_template(self.template_variables)
                self.subject = rendered['subject']
                self.message = rendered['content']
            except ValueError as e:
                # If template rendering fails, keep original content
                pass
        
        super().save(*args, **kwargs)


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
        ('push', 'Push Notification'),
    )
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='all')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='both')
    message = models.TextField()
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    template_variables = models.JSONField(default=dict, blank=True)
    
    # Scheduling and status
    scheduled_for = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Recipient tracking
    total_recipients = models.IntegerField(default=0)
    successful = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    
    # Custom audience filtering
    custom_filters = models.JSONField(default=dict, blank=True, help_text="JSON filters for custom audience")
    
    created_by = models.ForeignKey('users.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communications_broadcast'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['institution', 'status']),
            models.Index(fields=['scheduled_for', 'status']),
        ]
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Validate broadcast data"""
        if self.scheduled_for and self.scheduled_for < timezone.now():
            raise ValidationError('Scheduled time cannot be in the past')
        
        if self.template and self.template.template_type not in ['sms', 'email']:
            raise ValidationError('Template must be of type SMS or Email')
    
    def save(self, *args, **kwargs):
        """Auto-render template message if template is used"""
        if self.template and self.template_variables:
            try:
                rendered = self.template.render_template(self.template_variables)
                if self.template.template_type in ['sms', 'email']:
                    self.message = rendered['content']
            except ValueError as e:
                # If template rendering fails, keep original message
                pass
        
        super().save(*args, **kwargs)
    
    @property
    def progress_percentage(self):
        """Calculate broadcast progress percentage"""
        if self.total_recipients == 0:
            return 0
        return round((self.successful + self.failed) / self.total_recipients * 100, 1)
    
    @property
    def is_scheduled(self):
        """Check if broadcast is scheduled for future"""
        return self.status == 'scheduled' and self.scheduled_for and self.scheduled_for > timezone.now()
    
    @property
    def can_be_edited(self):
        """Check if broadcast can be edited"""
        return self.status in ['draft', 'failed']
    
    def start_processing(self):
        """Mark broadcast as processing"""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.save()
    
    def mark_completed(self):
        """Mark broadcast as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    def mark_failed(self):
        """Mark broadcast as failed"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.save()
    
    def update_stats(self, successful_count=0, failed_count=0):
        """Update broadcast statistics"""
        self.successful += successful_count
        self.failed += failed_count
        self.save()


class PushNotification(models.Model):
    """Model for push notifications"""
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    audience = models.CharField(max_length=20, choices=Broadcast.AUDIENCE_CHOICES, default='all')
    data = models.JSONField(default=dict, blank=True, help_text="Additional data payload")
    
    # Template integration
    template = models.ForeignKey(
        NotificationTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    template_variables = models.JSONField(default=dict, blank=True)
    
    scheduled_for = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Broadcast.STATUS_CHOICES, default='draft')
    
    total_recipients = models.IntegerField(default=0)
    successful = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    
    created_by = models.ForeignKey('users.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communications_push_notification'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


