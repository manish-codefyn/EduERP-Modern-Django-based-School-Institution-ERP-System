import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.timezone import now

class Attendance(models.Model):
    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('excused', 'Excused'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    remarks = models.TextField(blank=True)
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'attendance_attendance'
        unique_together = ['institution', 'student', 'date']
        permissions = [
            ("can_backdate", "Can mark/edit backdated attendance"),
        ]

    def __str__(self):
        return f"{self.student} - {self.date} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        """Enforce backdate rules at save time"""
        if self.marked_by and not self.marked_by.is_superuser:
            if not self.marked_by.has_perm("attendance.can_backdate"):
                if self.date != now().date():
                    raise ValidationError("You are not allowed to mark backdated attendance.")
        super().save(*args, **kwargs)

class StaffAttendance(models.Model):
    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('leave', 'Leave'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    staff = models.ForeignKey('hr.Staff', on_delete=models.CASCADE)  # Changed to HR Staff
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    remarks = models.TextField(blank=True)
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'attendance_staff_attendance'
        unique_together = ['institution', 'staff', 'date']
    
    def __str__(self):
        return f"{self.staff.user.get_full_name()} - {self.date} - {self.get_status_display()}"