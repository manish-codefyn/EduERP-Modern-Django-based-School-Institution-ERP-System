# accounts/adapter.py
from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomAccountAdapter(DefaultAccountAdapter):
    
    def get_login_redirect_url(self, request):
        """
        Redirect to student/parent dashboard or main admin dashboard
        """
        if request.user.is_authenticated:
            return self._get_role_based_redirect_url(request.user)
        return super().get_login_redirect_url(request)
    
    def _get_role_based_redirect_url(self, user):
        """
        Simplified redirect map with only two dashboards
        """
        # Roles that go to student/parent dashboard
        STUDENT_PARENT_ROLES = [
            User.Role.STUDENT,
            User.Role.PARENT,
        ]
        
        # Roles that go to main admin dashboard
        ADMIN_MAIN_ROLES = [
            User.Role.SUPERADMIN,
            User.Role.INSTITUTION_ADMIN,
            User.Role.PRINCIPAL,
            User.Role.TEACHER,
            User.Role.ACCOUNTANT,
            User.Role.LIBRARIAN,
            User.Role.TRANSPORT_MANAGER,
            User.Role.HR,
            User.Role.SUPPORT_STAFF,
            User.Role.LIBRARY_MANAGER,
        ]
        
        if user.role in STUDENT_PARENT_ROLES:
            return reverse('student_portal:dashboard')
        else:
            return reverse('dashboard')

# Alternative approach using if-else logic:
class SimpleAccountAdapter(DefaultAccountAdapter):
    
    def _get_role_based_redirect_url(self, user):
        """
        Simple if-else approach for two dashboards
        """
        if user.role in [User.Role.STUDENT, User.Role.PARENT]:
            return reverse('student_parent_dashboard')
        else:
            # All other roles go to admin main dashboard
            return reverse('admin_main_dashboard')