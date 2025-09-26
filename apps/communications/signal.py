# Signal handlers for automated functionality
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError

from apps.communications.models import NotificationTemplate,Notice
from .utils import TemplateRenderer

@receiver(pre_save, sender=NotificationTemplate)
def validate_template_syntax(sender, instance, **kwargs):
    """Validate template syntax before saving"""
    if instance.content:
        try:
            # Test template rendering with empty context
            TemplateRenderer.render_template(instance.content, {})
        except Exception as e:
            raise ValidationError(f"Template syntax error: {str(e)}")

@receiver(post_save, sender=Notice)
def create_audience_records(sender, instance, created, **kwargs):
    """Create audience records when notice is published"""
    if instance.is_published and instance.is_active:
        # This would typically be handled by a Celery task
        # For now, we'll just create a placeholder
        pass