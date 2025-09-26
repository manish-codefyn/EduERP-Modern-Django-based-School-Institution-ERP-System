# core/models.py
import uuid
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.base_user import BaseUserManager
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import secrets
import string


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular User with the given email and password.
        """
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
        """
        Create and save a SuperUser with the given email and password.
        """
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
        return ''.join(secrets.choice(alphabet) for i in range(length))


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # remove username field
    email = models.EmailField(_("email address"), unique=True)
    phone = models.CharField(_("phone number"), max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    last_seen = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # login using email
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    class Meta:
        db_table = "auth_user"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def role(self):
        """Shortcut to access user's profile role safely"""
        return getattr(self.profile, "role", None) if hasattr(self, 'profile') else None

    # Your role properties remain the same
    @property
    def is_superadmin(self):
        return self.role == "superadmin"

    @property
    def is_institution_admin(self):
        return self.role == "institution_admin"

    @property
    def is_principal(self):
        return self.role == "principal"

    @property
    def is_accountant(self):
        return self.role == "accountant"

    @property
    def is_teacher(self):
        return self.role == "teacher"

    @property
    def is_student(self):
        return self.role == "student"

    @property
    def is_parent(self):
        return self.role == "parent"

    @property
    def is_librarian(self):
        return self.role == "librarian"

    @property
    def is_transport_manager(self):
        return self.role == "transport_manager"

    @property
    def is_hr(self):
        return self.role == "hr"

    def send_welcome_email(self, password):
        """Send welcome email with login credentials"""
        subject = _("Welcome to Our School Management System")
        context = {
            'user': self,
            'password': password,
            'login_url': settings.FRONTEND_LOGIN_URL or settings.SITE_URL
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
            # Log this error in production
            print(f"Failed to send email: {e}")
            return False


class UserProfile(models.Model):
    ROLE_CHOICES = (
        ("superadmin", "Super Administrator"),
        ("institution_admin", "Institution Administrator"),
        ("principal", "Principal"),
        ("accountant", "Accountant"),
        ("teacher", "Teacher"),
        ("student", "Student"),
        ("parent", "Parent"),
        ("librarian", "Librarian"),
        ("transport_manager", "Transport Manager"),
        ("hr", "HR Manager"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
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

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} - {self.get_role_display()}"