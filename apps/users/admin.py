# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    """Inline UserProfile in User admin"""
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin"""
    model = User
    list_display = (
        "email",
        "get_full_name",
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
        "last_login",
        "created_at",
    )
    list_filter = (
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
        "created_at",
    )
    search_fields = ("email", "first_name", "last_name", "phone")
    ordering = ("-created_at",)
    readonly_fields = ("last_login", "created_at", "updated_at")
    inlines = [UserProfileInline]

    # Fields for detail/edit view
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "phone", "avatar", "date_of_birth")}),
        (_("Roles & Permissions"), {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "created_at", "updated_at")}),
    )

    # Fields for add user form
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role", "password1", "password2"),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """User Profile admin"""
    model = UserProfile
    list_display = ("user", "institution", "secondary_email", "is_active", "created_at")
    list_filter = ("is_active", "institution", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "secondary_email")
    ordering = ("-created_at",)
