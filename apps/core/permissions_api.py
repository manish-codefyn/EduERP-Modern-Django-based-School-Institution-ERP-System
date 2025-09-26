from rest_framework import permissions
from django.core.exceptions import ObjectDoesNotExist

class RoleBasedPermission(permissions.BasePermission):
    """
    Role-based permission system that checks user roles and their permissions
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

    def has_permission(self, request, view):
        # Superusers have all permissions
        if request.user.is_superuser:
            return True
            
        # Get the app label from the view
        app_label = self._get_app_label(view)
        
        # Get the action (view, add, change, delete)
        action = self._get_action(view)
        
        # Check if user's role has permission for this action
        user_role = request.user.role
        role_permissions = self.ROLE_PERMISSIONS.get(user_role, {})
        app_permissions = role_permissions.get(app_label, [])
        
        return action in app_permissions

    def _get_app_label(self, view):
        # Extract app label from view or model
        if hasattr(view, 'model'):
            return view.model._meta.app_label
        elif hasattr(view, 'queryset'):
            return view.queryset.model._meta.app_label
        else:
            # Fallback: try to get from view name or URL
            return view.__module__.split('.')[0]

    def _get_action(self, view):
        # Map view actions to permission types
        if hasattr(view, 'action'):
            action_map = {
                'list': 'view',
                'retrieve': 'view',
                'create': 'add',
                'update': 'change',
                'partial_update': 'change',
                'destroy': 'delete',
            }
            return action_map.get(view.action, 'view')
        else:
            # For class-based views without ViewSets
            return 'view'


class InstitutionPermission(permissions.BasePermission):
    """
    Permission to ensure users only access data from their institution
    """
    def has_object_permission(self, request, view, obj):
        # Superusers can access everything
        if request.user.is_superuser:
            return True
            
        # Check if object has institution field
        if hasattr(obj, 'institution'):
            user_institution = self._get_user_institution(request.user)
            return obj.institution == user_institution
            
        # For objects without institution field, check through relationships
        return self._check_related_institution(request.user, obj)

    def _get_user_institution(self, user):
        # Get user's institution from profile
        try:
            return user.profile.institution
        except ObjectDoesNotExist:
            return None

    def _check_related_institution(self, user, obj):
        # Recursively check related objects for institution
        user_institution = self._get_user_institution(user)
        
        # Check common relationship patterns
        for field in ['institution', 'school', 'college']:
            if hasattr(obj, field):
                related_institution = getattr(obj, field)
                return related_institution == user_institution
                
        # Check through foreign key relationships
        for field in obj._meta.get_fields():
            if field.is_relation and hasattr(field.related_model, 'institution'):
                try:
                    related_obj = getattr(obj, field.name)
                    if hasattr(related_obj, 'institution'):
                        return related_obj.institution == user_institution
                except ObjectDoesNotExist:
                    continue
                    
        return False