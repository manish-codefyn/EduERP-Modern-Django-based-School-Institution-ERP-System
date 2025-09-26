from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def user_can(user, action, model_name=None):
    """Check if user can perform action on model"""
    if user.is_superuser:
        return True
        
    # Simple role-based check for templates
    role_permissions = {
        'teacher': ['view'],
        'admin': ['view', 'add', 'change', 'delete'],
        'principal': ['view', 'add', 'change'],
    }
    
    return action in role_permissions.get(user.role, [])

@register.filter
def can_view(user, obj):
    """Check if user can view specific object"""
    if hasattr(obj, 'can_user_view'):
        return obj.can_user_view(user)
    return user.has_permission(obj._meta.app_label, 'view')