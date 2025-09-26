# student_portal/models.py
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class StudentProfile(models.Model):
    """Extended profile for student-specific data"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_portal_profile")
    student_id = models.CharField(max_length=20, unique=True)
    grade_level = models.CharField(max_length=10)
    section = models.CharField(max_length=10)
    academic_year = models.CharField(max_length=10)
    
    class Meta:
        db_table = "student_portal_profile"

class StudentAttendance(models.Model):
    """Student attendance records"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=[('present', 'Present'), ('absent', 'Absent')])
    
    class Meta:
        db_table = "student_portal_attendance"