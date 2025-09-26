# core/models.py
import uuid
import secrets
import string
from datetime import date

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            # Generate a random password if not provided
            password = self.generate_random_password()
            user.set_password(password)

        user.save(using=self._db)
        return user, password

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        user, password = self.create_user(email, password, **extra_fields)
        return user, password

    def generate_random_password(self, length=12):
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for _ in range(length))


class User(AbstractUser):
    """Custom User model using email as the primary identifier"""

    class Role(models.TextChoices):
        SUPERADMIN = "superadmin", "Super Administrator"
        INSTITUTION_ADMIN = "institution_admin", "Institution Administrator"
        PRINCIPAL = "principal", "Principal"
        ACCOUNTANT = "accountant", "Accountant"
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"
        PARENT = "parent", "Parent"
        LIBRARIAN = "librarian", "Librarian"
        TRANSPORT_MANAGER = "transport_manager", "Transport Manager"
        HR = "hr", "HR Manager"
        SUPPORT_STAFF = "support_staff", "Support Staff"
        LIBRARY_MANAGER = "LIBRARY_MANAGER", "Library Manager"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # disable username field
    email = models.EmailField(_("email address"), unique=True)

    phone = models.CharField(_("phone number"), max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    last_seen = models.DateTimeField(blank=True, null=True)

    # Role assignment (default = support staff)
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.SUPPORT_STAFF)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Login with email
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    class Meta:
        db_table = "auth_user"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.get_full_name() or self.email

    def get_full_name(self):
        """Return first_name + last_name with fallback to email."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email

    # Role-based checks
    @property
    def is_superadmin(self): return self.role == self.Role.SUPERADMIN
    @property
    def is_institution_admin(self): return self.role == self.Role.INSTITUTION_ADMIN
    @property
    def is_principal(self): return self.role == self.Role.PRINCIPAL
    @property
    def is_accountant(self): return self.role == self.Role.ACCOUNTANT
    @property
    def is_teacher(self): return self.role == self.Role.TEACHER
    @property
    def is_student(self): return self.role == self.Role.STUDENT
    @property
    def is_parent(self): return self.role == self.Role.PARENT
    @property
    def is_librarian(self): return self.role == self.Role.LIBRARIAN
    @property
    def is_transport_manager(self): return self.role == self.Role.TRANSPORT_MANAGER
    @property
    def is_hr(self): return self.role == self.Role.HR

    @property
    def is_management(self):
        return self.role in [
            self.Role.SUPERADMIN,
            self.Role.INSTITUTION_ADMIN,
            self.Role.PRINCIPAL,
        ]

    @property
    def is_academic_staff(self):
        return self.role in [
            self.Role.TEACHER,
            self.Role.PRINCIPAL,
            self.Role.LIBRARIAN,
        ]

    @property
    def is_administrative_staff(self):
        return self.role in [
            self.Role.HR,
            self.Role.ACCOUNTANT,
            self.Role.SUPPORT_STAFF,
            self.Role.INSTITUTION_ADMIN,
        ]

    @property
    def has_financial_access(self):
        return self.role in [
            self.Role.ACCOUNTANT,
            self.Role.INSTITUTION_ADMIN,
            self.Role.SUPERADMIN,
        ]

    # ========== PERMISSION METHODS ==========
    
    def has_permission(self, app_label, action, obj=None):
        """
        Check if user has specific permission for an app/object
        action: 'view', 'add', 'change', 'delete', 'export'
        """
        # Superadmins have all permissions
        if self.is_superadmin:
            return True
            
        # Get user's institution for object-level permissions
        user_institution = None
        if hasattr(self, 'profile') and self.profile.institution:
            user_institution = self.profile.institution

        # Define role permission matrix
        PERMISSION_MATRIX = {
            self.Role.SUPERADMIN: {
                'academics': ['view', 'add', 'change', 'delete', 'export'],
                'students': ['view', 'add', 'change', 'delete', 'export'],
                'teachers': ['view', 'add', 'change', 'delete', 'export'],
                'attendance': ['view', 'add', 'change', 'delete', 'export'],
                'hr': ['view', 'add', 'change', 'delete', 'export'],
                'finance': ['view', 'add', 'change', 'delete', 'export'],
                'library': ['view', 'add', 'change', 'delete', 'export'],
                'transport': ['view', 'add', 'change', 'delete', 'export'],
            },
            self.Role.INSTITUTION_ADMIN: {
                'academics': ['view', 'add', 'change', 'delete', 'export'],
                'students': ['view', 'add', 'change', 'delete', 'export'],
                'teachers': ['view', 'add', 'change', 'delete', 'export'],
                'attendance': ['view', 'add', 'change', 'delete', 'export'],
                'hr': ['view', 'add', 'change', 'delete', 'export'],
                'finance': ['view', 'add', 'change', 'delete', 'export'],
                'library': ['view', 'add', 'change', 'delete', 'export'],
                'transport': ['view', 'add', 'change', 'delete', 'export'],
            },
            self.Role.PRINCIPAL: {
                'academics': ['view', 'add', 'change', 'export'],
                'students': ['view', 'add', 'change', 'export'],
                'teachers': ['view', 'add', 'change', 'export'],
                'attendance': ['view', 'add', 'change', 'export'],
                'hr': ['view', 'export'],
                'finance': ['view', 'export'],
                'library': ['view', 'export'],
                'transport': ['view', 'export'],
            },
            self.Role.TEACHER: {
                'academics': ['view'],
                'students': ['view'],
                'attendance': ['view', 'add', 'change'],
                'library': ['view'],
            },
            self.Role.ACCOUNTANT: {
                'finance': ['view', 'add', 'change', 'export'],
                'students': ['view'],
                'attendance': ['view'],
            },
            self.Role.HR: {
                'hr': ['view', 'add', 'change', 'export'],
                'attendance': ['view', 'add', 'change', 'export'],
                'students': ['view'],
                'teachers': ['view', 'add', 'change', 'export'],
            },
            self.Role.STUDENT: {
                'academics': ['view'],
                'attendance': ['view'],  # Can view own attendance
                'library': ['view'],
            },
            self.Role.PARENT: {
                'students': ['view'],  # Can view own children
                'attendance': ['view'],  # Can view children's attendance
                'academics': ['view'],  # Can view academic info
            },
            self.Role.LIBRARIAN: {
                'library': ['view', 'add', 'change', 'export'],
                'students': ['view'],
            },
            self.Role.TRANSPORT_MANAGER: {
                'transport': ['view', 'add', 'change', 'export'],
                'students': ['view'],
            },
            self.Role.SUPPORT_STAFF: {
                # Limited access based on specific assignments
            }
        }

        # Check basic permission from matrix
        role_perms = PERMISSION_MATRIX.get(self.role, {})
        app_perms = role_perms.get(app_label, [])
        
        if action not in app_perms:
            return False
            
        # Object-level permission checks
        if obj and user_institution:
            # Check if object belongs to user's institution
            if hasattr(obj, 'institution') and obj.institution != user_institution:
                return False
                
            # Special object-level checks
            if app_label == 'students' and self.role == self.Role.TEACHER:
                # Teachers can only view students in their classes
                from academics.models import Class  # Import here to avoid circular imports
                if hasattr(obj, 'student_classes'):
                    return obj.student_classes.filter(teacher__user=self).exists()
                    
            elif app_label == 'students' and self.role == self.Role.PARENT:
                # Parents can only view their own children
                return obj.parents.filter(user=self).exists()
                
        return True

    def can_view(self, app_label, obj=None):
        """Check if user can view objects in app"""
        return self.has_permission(app_label, 'view', obj)
        
    def can_add(self, app_label, obj=None):
        """Check if user can add objects in app"""
        return self.has_permission(app_label, 'add', obj)
        
    def can_change(self, app_label, obj=None):
        """Check if user can change objects in app"""
        return self.has_permission(app_label, 'change', obj)
        
    def can_delete(self, app_label, obj=None):
        """Check if user can delete objects in app"""
        return self.has_permission(app_label, 'delete', obj)
        
    def can_export(self, app_label, obj=None):
        """Check if user can export objects in app"""
        return self.has_permission(app_label, 'export', obj)

    # Specific permission methods for common use cases
    def can_view_student(self, student):
        """Check if user can view specific student"""
        return self.has_permission('students', 'view', student)
        
    def can_edit_student(self, student):
        """Check if user can edit specific student"""
        return self.has_permission('students', 'change', student)
        
    def can_delete_student(self, student):
        """Check if user can delete specific student"""
        return self.has_permission('students', 'delete', student)
        
    def can_view_attendance(self, attendance):
        """Check if user can view specific attendance record"""
        return self.has_permission('attendance', 'view', attendance)
        
    def can_mark_attendance(self, attendance):
        """Check if user can mark attendance"""
        return self.has_permission('attendance', 'add', attendance)
        
    def can_edit_attendance(self, attendance):
        """Check if user can edit attendance"""
        return self.has_permission('attendance', 'change', attendance)

    def can_access_finance(self):
        """Check if user has financial access"""
        return self.has_permission('finance', 'view')
        
    def can_manage_hr(self):
        """Check if user can manage HR functions"""
        return self.has_permission('hr', 'view')

    def get_accessible_apps(self):
        """Get list of apps user can access"""
        PERMISSION_MATRIX = {
            self.Role.SUPERADMIN: ['academics', 'students', 'teachers', 'attendance', 'hr', 'finance', 'library', 'transport'],
            self.Role.INSTITUTION_ADMIN: ['academics', 'students', 'teachers', 'attendance', 'hr', 'finance', 'library', 'transport'],
            self.Role.PRINCIPAL: ['academics', 'students', 'teachers', 'attendance', 'hr', 'finance', 'library', 'transport'],
            self.Role.TEACHER: ['academics', 'students', 'attendance', 'library'],
            self.Role.ACCOUNTANT: ['finance', 'students', 'attendance'],
            self.Role.HR: ['hr', 'attendance', 'students', 'teachers'],
            self.Role.STUDENT: ['academics', 'attendance', 'library'],
            self.Role.PARENT: ['students', 'attendance', 'academics'],
            self.Role.LIBRARIAN: ['library', 'students'],
            self.Role.TRANSPORT_MANAGER: ['transport', 'students'],
            self.Role.SUPPORT_STAFF: [],
        }
        return PERMISSION_MATRIX.get(self.role, [])

    def get_permitted_actions(self, app_label):
        """Get list of actions user can perform in an app"""
        PERMISSION_MATRIX = {
            self.Role.SUPERADMIN: {
                'academics': ['view', 'add', 'change', 'delete', 'export'],
                'students': ['view', 'add', 'change', 'delete', 'export'],
                # ... other apps
            },
            # ... other roles
        }
        role_perms = PERMISSION_MATRIX.get(self.role, {})
        return role_perms.get(app_label, [])

    def send_welcome_email(self, password):
        """Send welcome email with login credentials"""
        subject = _("Welcome to Our School Management System")
        context = {
            'user': self,
            'password': password,
            'login_url': getattr(settings, "FRONTEND_LOGIN_URL", settings.SITE_URL),
        }

        html_message = render_to_string('emails/welcome_teacher.html', context)
        plain_message = render_to_string('emails/welcome_teacher.txt', context)

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.email],
                html_message=html_message,
                fail_silently=False,
            )
            return True
        except Exception as e:
            # In production, log the error instead of printing
            print(f"Failed to send email: {e}")
            return False

class UserProfile(models.Model):
    """Extra profile data for users, linked to institutions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    institution = models.ForeignKey(
        "organization.Institution", on_delete=models.CASCADE, null=True, blank=True
    )
    address = models.TextField(blank=True)
    secondary_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_user_profile"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.user.get_role_display()}"

    def get_age(self):
        """Calculate age from date_of_birth"""
        if self.user.date_of_birth:
            today = date.today()
            return today.year - self.user.date_of_birth.year - (
                (today.month, today.day) < (self.user.date_of_birth.month, self.user.date_of_birth.day)
            )
        return None
