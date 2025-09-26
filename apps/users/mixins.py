# core/mixins.py
import logging
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .models import User

logger = logging.getLogger(__name__)


class RoleRequiredMixin(AccessMixin):
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


# Specific role mixins (using User.Role constants)

class DirectorRequiredMixin(RoleRequiredMixin):
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.PRINCIPAL,
    ]
    permission_denied_message = _("Director-level access required.")


class PrincipalRequiredMixin(RoleRequiredMixin):
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.PRINCIPAL,
    ]
    permission_denied_message = _("Principal-level access required.")


class FinanceAccessRequiredMixin(RoleRequiredMixin):
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.ACCOUNTANT,
    ]
    permission_denied_message = _("Financial access required.")


class HRAccessRequiredMixin(RoleRequiredMixin):
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.HR,
    ]
    permission_denied_message = _("HR access required.")


class TeacherRequiredMixin(RoleRequiredMixin):
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.PRINCIPAL,
        User.Role.TEACHER,
    ]
    permission_denied_message = _("Teacher access required.")
    
class TeacherManagementRequiredMixin(RoleRequiredMixin):
    allowed_roles = [
        User.Role.SUPERADMIN,
        User.Role.INSTITUTION_ADMIN,
        User.Role.PRINCIPAL,
        User.Role.HR,  # If HR should manage teachers too
    ]
    permission_denied_message = _("Teacher management access required.")
