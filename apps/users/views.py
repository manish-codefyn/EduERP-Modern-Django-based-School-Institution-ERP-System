# accounts/views.py
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model

User = get_user_model()


class RoleBasedDashboardView(LoginRequiredMixin, TemplateView):
    """Base class for both dashboards"""
    template_name = 'accounts/dashboard_base.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_role'] = self.request.user.role
        context['user'] = self.request.user
        context['role_display'] = self.request.user.get_role_display()
        return context

class StudentParentDashboardView(RoleBasedDashboardView):
    """Dashboard for Students and Parents"""
    template_name = 'accounts/student_parent_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Role-specific context
        if self.request.user.is_student:
            context['page_title'] = 'Student Dashboard'
            context['dashboard_type'] = 'student'
            context['can_view_academics'] = self.request.user.can_view('academics')
            context['can_view_attendance'] = self.request.user.can_view_attendance(None)
            
        elif self.request.user.is_parent:
            context['page_title'] = 'Parent Dashboard'
            context['dashboard_type'] = 'parent'
            context['can_view_children'] = self.request.user.can_view_student(None)
            context['can_view_academics'] = self.request.user.can_view('academics')
        
        return context

class AdminMainDashboardView(RoleBasedDashboardView):
    """Main dashboard for all admin/staff roles"""
    template_name = 'accounts/admin_main_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'{self.request.user.get_role_display()} Dashboard'
        
        # Add role-specific features
        context['is_management'] = self.request.user.is_management
        context['is_academic_staff'] = self.request.user.is_academic_staff
        context['is_administrative_staff'] = self.request.user.is_administrative_staff
        context['has_financial_access'] = self.request.user.has_financial_access
        
        # Accessible apps for this user
        context['accessible_apps'] = self.request.user.get_accessible_apps()
        
        # Role-based permissions summary
        context['permissions'] = {
            'can_manage_students': self.request.user.can_view_student(None),
            'can_manage_attendance': self.request.user.can_view_attendance(None),
            'can_access_finance': self.request.user.can_access_finance(),
            'can_manage_hr': self.request.user.can_manage_hr(),
        }
        
        return context

# Fallback profile view
class ProfileView(RoleBasedDashboardView):
    template_name = 'accounts/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'User Profile'
        return context