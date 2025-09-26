# student_portal/models.py
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class StudentProfile(models.Model):
    """Extended profile for student-specific data"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_portal_profile")
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20)
    grade_level = models.CharField(max_length=10)
    section = models.CharField(max_length=10)
    academic_year = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "student_portal_profile"
        unique_together = ['institution', 'student_id']  # Student ID unique per institution

    def __str__(self):
        return f"{self.student_id} - {self.user.get_full_name()}"

class StudentAttendance(models.Model):
    """Student attendance records"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=[
        ('present', 'Present'), 
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day')
    ])
    subject = models.ForeignKey('academics.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='recorded_attendances')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "student_portal_attendance"
        unique_together = ['institution', 'student', 'date', 'subject']  # One record per student per day per subject
        indexes = [
            models.Index(fields=['institution', 'date']),
            models.Index(fields=['student', 'date']),
        ]

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.date} - {self.status}"

class StudentGrade(models.Model):
    """Student grades and results"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE)
    exam_type = models.ForeignKey('examination.ExamType', on_delete=models.CASCADE)
    grade = models.CharField(max_length=5)
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    total_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    grade_date = models.DateField()
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "student_portal_grade"
        unique_together = ['institution', 'student', 'subject', 'exam_type', 'grade_date']

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.subject.name} - {self.grade}"

class StudentTimetable(models.Model):
    """Student class timetable"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    grade_level = models.CharField(max_length=10)
    section = models.CharField(max_length=10)
    day_of_week = models.IntegerField(choices=[
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), 
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')
    ])
    period = models.IntegerField()
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': User.Role.TEACHER})
    classroom = models.CharField(max_length=50, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = "student_portal_timetable"
        unique_together = ['institution', 'grade_level', 'section', 'day_of_week', 'period']
        ordering = ['day_of_week', 'period']

    def __str__(self):
        return f"{self.get_day_of_week_display()} P{self.period} - {self.subject.name}"

class LearningResource(models.Model):
    """Learning resources for students"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    resource_type = models.CharField(max_length=20, choices=[
        ('pdf', 'PDF'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('link', 'Web Link'),
        ('audio', 'Audio')
    ])
    file = models.FileField(upload_to='learning_resources/', blank=True, null=True)
    external_url = models.URLField(blank=True)
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE)
    grade_level = models.CharField(max_length=10)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)
    published_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "student_portal_learning_resource"
        indexes = [
            models.Index(fields=['institution', 'grade_level', 'subject']),
        ]

    def __str__(self):
        return f"{self.title} - {self.grade_level}"

class StudentAnnouncement(models.Model):
    """Announcements specific to students"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    target_grade = models.CharField(max_length=10, blank=True)  # Empty for all grades
    target_section = models.CharField(max_length=10, blank=True)  # Empty for all sections
    priority = models.CharField(max_length=10, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='medium')
    published_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    publish_date = models.DateTimeField()
    expiry_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "student_portal_announcement"
        indexes = [
            models.Index(fields=['institution', 'publish_date']),
        ]
        ordering = ['-publish_date']

    def __str__(self):
        return self.title