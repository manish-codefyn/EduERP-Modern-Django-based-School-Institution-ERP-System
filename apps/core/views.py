from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views.generic import View
from django.contrib.auth.mixins import UserPassesTestMixin
from .permissions import RoleBasedPermissionMixin
from apps.academics.models import AcademicYear


class DashboardView(TemplateView):
    template_name = 'index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add dashboard data here
        return context



def handler404(request, exception):
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    return render(request, 'errors/500.html', status=500)


class RoleBasedViewMixin(UserPassesTestMixin):
    """
    Mixin for class-based views to enforce role-based permissions
    """
    # Define which roles can access this view
    allowed_roles = []
    # Define specific permissions required
    required_permissions = []
    
    def test_func(self):
        user = self.request.user
        
        # Superusers have access to everything
        if user.is_superuser:
            return True
            
        # Check if user role is allowed
        if self.allowed_roles and user.role not in self.allowed_roles:
            return False
            
        # Check specific permissions if defined
        if self.required_permissions:
            # Get the app label from the model (if available)
            app_label = None
            if hasattr(self, 'model'):
                app_label = self.model._meta.app_label
                
            # Check each required permission
            for permission in self.required_permissions:
                if not self._has_permission(user, app_label, permission):
                    return False
                    
        return True
    
    def _has_permission(self, user, app_label, permission):
        # Simplified permission check
        # You can integrate with the full permission system from permissions.py
        role_permissions = {
            'superadmin': ['view', 'add', 'change', 'delete', 'export'],
            'institution_admin': ['view', 'add', 'change', 'delete', 'export'],
            'principal': ['view', 'add', 'change', 'export'],
            'teacher': ['view', 'add', 'change'],
            'student': ['view'],
            'parent': ['view'],
            'hr': ['view', 'add', 'change', 'export'],
            'accountant': ['view', 'add', 'change', 'export'],
        }
        
        user_permissions = role_permissions.get(user.role, ['view'])
        return permission in user_permissions


class AcademicsBaseView(RoleBasedViewMixin, View):
    """
    Base class for academics views with role-based access control
    """
    allowed_roles = [
        'superadmin', 'institution_admin', 'principal', 
        'teacher', 'accountant', 'hr'
    ]
    
    def get_institution(self):
        """Get institution from the logged-in user's profile."""
        user = self.request.user
        if hasattr(user, 'profile') and hasattr(user.profile, 'institution'):
            return user.profile.institution
        return None
    
    def get_current_academic_year(self):
        """Get current academic year for the institution."""
        institution = self.get_institution()
        if institution:
            try:
                return AcademicYear.objects.filter(
                    is_current=True, 
                    institution=institution
                ).first()
            except AcademicYear.DoesNotExist:
                return None
        return None
    
    def get_queryset(self):
        """Filter queryset by user's institution and role"""
        queryset = super().get_queryset()
        institution = self.get_institution()
        
        if institution and hasattr(queryset.model, 'institution'):
            queryset = queryset.filter(institution=institution)
            
        # Additional role-based filtering
        if self.request.user.role == 'teacher':
            # Teachers can only see their own classes/students
            if hasattr(queryset.model, 'teacher'):
                queryset = queryset.filter(teacher__user=self.request.user)
                
        return queryset