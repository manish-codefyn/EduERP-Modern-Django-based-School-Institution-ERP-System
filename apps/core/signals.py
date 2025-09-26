# core/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from apps.users.models import  User, UserProfile
from apps.students.models import Student
import uuid

@receiver(pre_save, sender=Student)
def create_user_for_student(sender, instance, **kwargs):
    """
    Automatically create User if not already set when Student is being saved.
    """
    if not instance.user_id:
        # Generate a temporary email if not provided
        if not hasattr(instance, 'email') or not instance.email:
            email = f"{uuid.uuid4().hex[:8]}@example.com"
        else:
            email = instance.email

        # Create the User
        user = User.objects.create(
            first_name=getattr(instance, 'first_name', 'First'),
            last_name=getattr(instance, 'last_name', 'Last'),
            email=email,
            phone=getattr(instance, 'guardian_phone', ''),
        )
        instance.user = user


@receiver(post_save, sender=Student)
def create_user_profile_for_student(sender, instance, created, **kwargs):
    """
    Automatically create UserProfile when a new Student is created.
    """
    if created:
        # Ensure the user has the student role
        if instance.user.role != instance.user.Role.STUDENT:
            instance.user.role = instance.user.Role.STUDENT
            instance.user.save(update_fields=['role'])

        UserProfile.objects.get_or_create(
            user=instance.user,
            defaults={
                "institution": instance.institution
            }
        )
