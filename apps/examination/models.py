import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class ExamType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'examination_exam_type'
        unique_together = ['institution', 'code']
    
    def __str__(self):
        return self.name

class Exam(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    exam_type = models.ForeignKey(ExamType, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    academic_year = models.ForeignKey('academics.AcademicYear', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'examination_exam'
    
    def __str__(self):
        return f"{self.name} - {self.academic_year}"
    
    @property
    def duration(self):
        """Returns duration of the exam in a human-readable format (days)."""
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            if delta.days == 0:
                return "1 day"
            return f"{delta.days + 1} days"  # +1 to include both start and end
        return "N/A"
        
    @property
    def get_status_display(self):
        """
        Returns a human-readable status string: 'Upcoming', 'Ongoing', 'Completed', or 'Cancelled'.
        """
        today = timezone.now().date()

        if not self.is_published:
            return "Cancelled"
        if self.start_date > today:
            return "Upcoming"
        elif self.start_date <= today <= self.end_date:
            return "Ongoing"
        elif self.end_date < today:
            return "Completed"
        return "N/A"

    @property
    def get_status_badge(self):
        """
        Returns a Bootstrap badge class based on status.
        """
        status = self.get_status_display
        if status == "Upcoming":
            return "bg-info"
        elif status == "Ongoing":
            return "bg-warning"
        elif status == "Completed":
            return "bg-success"
        elif status == "Cancelled":
            return "bg-danger"
        return "bg-secondary"


class ExamSubject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='subjects')
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE)
    max_marks = models.DecimalField(max_digits=5, decimal_places=2)
    pass_marks = models.DecimalField(max_digits=5, decimal_places=2)
    exam_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'examination_exam_subject'
        unique_together = ['exam', 'subject']
    
    def __str__(self):
        return f"{self.exam} - {self.subject}"
    
    @property
    def total_marks(self):
        """
        Returns the total marks for this exam subject.
        """
        return self.max_marks if self.max_marks else 0

class ExamResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam_subject = models.ForeignKey(ExamSubject, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=5, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'examination_exam_result'
        unique_together = ['exam_subject', 'student']
    
    def __str__(self):
        return f"{self.student} - {self.exam_subject}"
    
    def save(self, *args, **kwargs):
        # Calculate grade based on marks
        percentage = (self.marks_obtained / self.exam_subject.max_marks) * 100
        
        if percentage >= 90:
            self.grade = 'A+'
        elif percentage >= 80:
            self.grade = 'A'
        elif percentage >= 70:
            self.grade = 'B+'
        elif percentage >= 60:
            self.grade = 'B'
        elif percentage >= 50:
            self.grade = 'C'
        elif percentage >= 40:
            self.grade = 'D'
        else:
            self.grade = 'F'
            
        super().save(*args, **kwargs)

    @property
    def status(self):
        """
        Returns 'Pass' or 'Fail' based on pass_marks of the exam_subject.
        """
        if self.marks_obtained >= self.exam_subject.pass_marks:
            return "Pass"
        return "Fail"
