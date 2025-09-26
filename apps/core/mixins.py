# core/mixins.py
import logging
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from apps.users.models import User
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect,render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
logger = logging.getLogger(__name__),


class RoleRequiredMixin(LoginRequiredMixin,AccessMixin):
    """Verify that the current user has the required role."""

    allowed_roles: list = None
    permission_denied_message = _("You don't have permission to access this page.")
    redirect_url = "dashboard"  # Default redirect (can be overridden)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if self.allowed_roles and (
            not hasattr(request.user, "role") or request.user.role not in self.allowed_roles
        ):
            logger.warning(
                f"Unauthorized access attempt by {request.user.email} "
                f"(role={getattr(request.user, 'role', None)}) → {request.path}"
            )
            messages.error(request, self.permission_denied_message)
            return redirect(self.redirect_url)

        return super().dispatch(request, *args, **kwargs)


class InstitutionMixin:
    """Mixin to handle institution-based filtering"""
    
    def get_queryset(self):
        queryset = super().get_queryset()
        institution_id = self.kwargs.get('institution_id') or self.request.session.get('current_institution')
        if institution_id and hasattr(queryset.model, 'institution'):
            return queryset.filter(institution_id=institution_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution_id = self.kwargs.get('institution_id') or self.request.session.get('current_institution')
        if institution_id:
            from organization.models import Institution
            context['current_institution'] = get_object_or_404(Institution, id=institution_id)
        return context

    def form_valid(self, form):
        institution_id = self.kwargs.get('institution_id') or self.request.session.get('current_institution')
        if institution_id and hasattr(form.instance, 'institution'):
            from organization.models import Institution
            form.instance.institution = get_object_or_404(Institution, id=institution_id)
        return super().form_valid(form)
    

class HRRequiredMixin(RoleRequiredMixin,InstitutionMixin):
    """General HR access required for HR users."""
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.HR,
    ]
    permission_denied_message = _("HR access required.")


class DirectorRequiredMixin(RoleRequiredMixin,InstitutionMixin):
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.PRINCIPAL,
    ]
    permission_denied_message = _("Director-level access required.")


class PrincipalRequiredMixin(RoleRequiredMixin,InstitutionMixin):
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.PRINCIPAL,
    ]
    permission_denied_message = _("Principal-level access required.")


class FinanceAccessRequiredMixin(RoleRequiredMixin,InstitutionMixin):
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.ACCOUNTANT,
    ]
    permission_denied_message = _("Financial access required.")


class HRAccessRequiredMixin(RoleRequiredMixin,InstitutionMixin):
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.HR,
    ]
    permission_denied_message = _("HR access required.")


class TeacherRequiredMixin(RoleRequiredMixin,InstitutionMixin):
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.PRINCIPAL,
        User.Role.TEACHER,
    ]
    permission_denied_message = _("Teacher access required.")
    
class TeacherManagementRequiredMixin(RoleRequiredMixin,InstitutionMixin):
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.PRINCIPAL,
        User.Role.HR,  # If HR should manage teachers too
    ]
    permission_denied_message = _("Teacher management access required.")


class ManagementRequiredMixin(RoleRequiredMixin,InstitutionMixin):
    """
    Base mixin for entity (teacher/staff/student) management.
    Restricts access based on allowed roles.
    """
    entity_name = "management"  # override in subclasses
    allowed_roles = []  # override in subclasses

    @property
    def permission_denied_message(self):
        return _(f"{self.entity_name.capitalize()} access required.")


class TeacherManagementRequiredMixin(ManagementRequiredMixin,InstitutionMixin):
    entity_name = "teacher"
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.PRINCIPAL,
        User.Role.HR,
    ]


class StaffManagementRequiredMixin(ManagementRequiredMixin,InstitutionMixin):
    entity_name = "staff"
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.PRINCIPAL,
        User.Role.HR,
    ]


class StudentManagementRequiredMixin(ManagementRequiredMixin,InstitutionMixin):
    entity_name = "student"
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.PRINCIPAL,
        User.Role.TEACHER,   # usually teachers also manage students
    ]
    

class HRManagementRequiredMixin(ManagementRequiredMixin,InstitutionMixin):
    """Access required for managing HR staff."""
    entity_name = "HR"
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
    ]


class StaffRequiredMixin:
    """
    Restrict access to users who are staff members.
    Works with your Staff model relation (user.staff_profile).
    """
    permission_denied_message = _("Only staff members can access this page.")
    redirect_url = "account_login"  # change to your login URL or dashboard

    def dispatch(self, request, *args, **kwargs):
        # User must be authenticated
        if not request.user.is_authenticated:
            messages.error(request, self.permission_denied_message)
            return redirect(self.redirect_url)

        # User must have a linked Staff profile
        if not hasattr(request.user, 'staff_profile'):
            messages.error(request, self.permission_denied_message)
            return redirect(self.redirect_url)

        return super().dispatch(request, *args, **kwargs)
    

class LibraryManagerRequiredMixin(RoleRequiredMixin,InstitutionMixin):
    """Restrict access to Library Managers (and higher roles if needed)."""
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.LIBRARIAN,
    ]
    permission_denied_message = _("Library Manager access required.")


class StudentPortalMixin:
    """Mixin to ensure only students can access these views"""
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_student:
            from django.shortcuts import redirect
            return redirect('access_denied')
        return super().dispatch(request, *args, **kwargs)
    


class StudentRequiredMixin:
    """
    Mixin to restrict access to students of a specific institution.
    Optionally, can restrict by roles if needed.
    """

    allowed_roles = [
        User.Role.SUPERADMIN,        # Optional, if staff can also access
        User.Role.INSTITUTION_ADMIN, # Optional
        User.Role.STUDENT,           # Default student role
    ]
    permission_denied_message = _("You must be a student of this institution to access this page.")
    redirect_url = reverse_lazy("home")  # Default redirect if permission denied

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        user = request.user

        # Ensure user role is allowed
        if hasattr(user, "role") and user.role not in self.allowed_roles:
            messages.error(request, self.permission_denied_message)
            return redirect(self.redirect_url)

        # Ensure the user has an institution
        institution = getattr(user, "institution", None)
        if not institution:
            messages.error(request, _("No institution assigned to your account."))
            return redirect(self.redirect_url)

        # Optional: If the view passes an institution id, match it
        view_institution_id = self.kwargs.get("institution_id")
        if view_institution_id and str(institution.id) != str(view_institution_id):
            messages.error(request, _("You are not allowed to access this institution's resources."))
            return redirect(self.redirect_url)

        return super().dispatch(request, *args, **kwargs)   