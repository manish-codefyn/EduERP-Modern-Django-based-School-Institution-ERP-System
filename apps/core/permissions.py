# core/permissions_views.py
from django.http import HttpResponseForbidden
from django.core.exceptions import ObjectDoesNotExist

class RoleBasedPermissionMixin:
    """
    Role-based permission mixin for normal CBVs
    """
       # Define role permissions matrix
    ROLE_PERMISSIONS = {
        'superadmin': {
            'academics': ['view', 'add', 'change', 'delete', 'export'],
            'students': ['view', 'add', 'change', 'delete', 'export'],
            'teachers': ['view', 'add', 'change', 'delete', 'export'],
            'attendance': ['view', 'add', 'change', 'delete', 'export'],
            'hr': ['view', 'add', 'change', 'delete', 'export'],
            'finance': ['view', 'add', 'change', 'delete', 'export'],
        },
        'institution_admin': {
            'academics': ['view', 'add', 'change', 'delete', 'export'],
            'students': ['view', 'add', 'change', 'delete', 'export'],
            'teachers': ['view', 'add', 'change', 'delete', 'export'],
            'attendance': ['view', 'add', 'change', 'delete', 'export'],
            'hr': ['view', 'add', 'change', 'delete', 'export'],
            'finance': ['view', 'add', 'change', 'delete', 'export'],
        },
        'principal': {
            'academics': ['view', 'add', 'change', 'export'],
            'students': ['view', 'add', 'change', 'export'],
            'teachers': ['view', 'add', 'change', 'export'],
            'attendance': ['view', 'add', 'change', 'export'],
            'hr': ['view', 'export'],
            'finance': ['view', 'export'],
        },
        'teacher': {
            'academics': ['view', 'export'],
            'students': ['view', 'export'],
            'attendance': ['view', 'add', 'change', 'export'],
            'hr': [],  # No access to HR
            'finance': [],  # No access to finance
        },
        'accountant': {
            'finance': ['view', 'add', 'change', 'export'],
            'students': ['view'],  # For fee-related operations
            'attendance': ['view'],  # For payroll calculations
        },
        'hr': {
            'hr': ['view', 'add', 'change', 'export'],
            'attendance': ['view', 'add', 'change', 'export'],
            'students': ['view'],
            'teachers': ['view', 'add', 'change', 'export'],
        },
        'student': {
            'academics': ['view'],
            'attendance': ['view'],  # Can view own attendance
        },
        'parent': {
            'students': ['view'],  # Can view own children
            'attendance': ['view'],  # Can view children's attendance
            'academics': ['view'],  # Can view academic info
        },
        'librarian': {
            'library': ['view', 'add', 'change', 'export'],
        },
        'transport_manager': {
            'transport': ['view', 'add', 'change', 'export'],
            'students': ['view'],
        },
        'support_staff': {
            # Limited access based on specific assignments
        }
        
        }
    required_permission = 'view'

    def has_permission(self):
        user = self.request.user
        if user.is_superuser:
            return True

        app_label = getattr(self.model, '_meta').app_label
        role_permissions = self.ROLE_PERMISSIONS.get(getattr(user, 'role', None), {})
        app_permissions = role_permissions.get(app_label, [])
        return self.required_permission in app_permissions

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            return HttpResponseForbidden("You don't have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)


class InstitutionPermissionMixin:
    """
    Institution-based permission mixin for CBVs
    """
    def has_object_permission(self, obj):
        user = self.request.user
        if user.is_superuser:
            return True
        try:
            user_institution = user.profile.institution
        except AttributeError:
            user_institution = None

        if hasattr(obj, 'institution'):
            return obj.institution == user_institution

        for field in ['school', 'college']:
            if hasattr(obj, field):
                return getattr(obj, field) == user_institution
        return False

    def get_queryset(self, queryset=None):
        if queryset is None:
            queryset = super().get_queryset()
        try:
            user_institution = self.request.user.profile.institution
        except AttributeError:
            return queryset.none()

        if hasattr(self.model, 'institution'):
            return queryset.filter(institution=user_institution)
        return queryset
