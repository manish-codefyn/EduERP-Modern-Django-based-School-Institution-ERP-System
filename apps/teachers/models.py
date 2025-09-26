import uuid
from django.db import models
from django.http import HttpResponse
from django.urls import reverse
from utils.utils import qr_generate,render_to_pdf
import uuid
import io
import os
import csv
from io import BytesIO
from django.utils import timezone
import qrcode
from PIL import Image, ImageDraw, ImageFont
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from django.conf import settings
import qrcode
from io import BytesIO
import base64
import random


class Teacher(models.Model):
    QUALIFICATION_CHOICES = (
        ('phd', 'PhD'),
        ('masters', 'Masters'),
        ('bachelors', 'Bachelors'),
        ('diploma', 'Diploma'),
        ('other', 'Other'),
    )

    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )

    ORGANIZATION_TYPE_CHOICES = (
        ('institute', 'Institute'),
        ('school', 'School'),
        ('college', 'College'),
        ('university', 'University'),
        ('coaching', 'Coaching Center'),
        ('other', 'Other'),
    )

    DEPARTMENT_CHOICES = (
        ('science', 'Science'),
        ('commerce', 'Commerce'),
        ('arts', 'Arts'),
        ('computer', 'Computer Science'),
        ('mathematics', 'Mathematics'),
        ('physics', 'Physics'),
        ('chemistry', 'Chemistry'),
        ('biology', 'Biology'),
        ('english', 'English'),
        ('social_science', 'Social Science'),
        ('physical_education', 'Physical Education'),
        ('languages', 'Languages'),
        ('other', 'Other'),
    )

    DESIGNATION_CHOICES = (
        ('principal', 'Principal'),
        ('vice_principal', 'Vice Principal'),
        ('headmaster', 'Headmaster'),
        ('headmistress', 'Headmistress'),
        ('professor', 'Professor'),
        ('associate_professor', 'Associate Professor'),
        ('assistant_professor', 'Assistant Professor'),
        ('lecturer', 'Lecturer'),
        ('senior_teacher', 'Senior Teacher'),
        ('teacher', 'Teacher'),
        ('tutor', 'Tutor'),
        ('visiting_faculty', 'Visiting Faculty'),
        ('guest_lecturer', 'Guest Lecturer'),
        ('other', 'Other'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        null=True,
        blank=True
    )
    institution = models.ForeignKey(
        'organization.Institution', on_delete=models.CASCADE
    )
    employee_id = models.CharField(max_length=50, unique=True, blank=True)

    # Personal details
    first_name = models.CharField(max_length=150)
    middle_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=15)  # Increased length for international numbers
    dob = models.DateField(verbose_name="Date of Birth", null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    blood_group = models.CharField(max_length=5, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=15)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)

    # Professional details
    qualification = models.CharField(max_length=20, choices=QUALIFICATION_CHOICES)
    specialization = models.CharField(max_length=100, blank=True)
    joining_date = models.DateField()
    experience = models.IntegerField(default=0)
    salary = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True  # Increased for higher salaries
    )
    is_class_teacher = models.BooleanField(default=False)
    
    # Organization-specific fields
    organization_type = models.CharField(
        max_length=20, 
        choices=ORGANIZATION_TYPE_CHOICES, 
        default='school'
    )
    department = models.CharField(
        max_length=50, 
        choices=DEPARTMENT_CHOICES, 
        blank=True, 
        null=True
    )
    designation = models.CharField(
        max_length=50, 
        choices=DESIGNATION_CHOICES, 
        default='teacher'
    )
    faculty_type = models.CharField(
        max_length=20,
        choices=(
            ('regular', 'Regular'),
            ('visiting', 'Visiting'),
            ('guest', 'Guest'),
            ('contract', 'Contract'),
            ('part_time', 'Part Time'),
        ),
        default='regular'
    )
    teaching_grade_levels = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Grade levels taught (e.g., 9-12, Undergraduate, etc.)"
    )

    # Relationships
    subjects = models.ManyToManyField(
        'academics.Subject', related_name='teachers', blank=True
    )
    class_teacher_of = models.ForeignKey(
        'academics.Class',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_teacher'
    )
    department_head = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='department_members'
    )

    # Media
    photo = models.ImageField(upload_to='teacher_photos/', blank=True, null=True)
    resume = models.FileField(upload_to='teacher_resumes/', blank=True, null=True)
    degree_certificates = models.FileField(
        upload_to='teacher_certificates/', 
        blank=True, 
        null=True,
        help_text="Upload degree certificates"
    )

    # System fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teachers_teacher'
        ordering = ['first_name', 'last_name']
        indexes = [
            models.Index(fields=['organization_type']),
            models.Index(fields=['department']),
            models.Index(fields=['designation']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        full_name = f"{self.first_name} {self.middle_name or ''} {self.last_name}".strip()
        return f"{full_name} ({self.employee_id}) - {self.get_designation_display()}"
 
    @property
    def name(self):
        """Return the full name for use in success messages"""
        return self.get_full_name()
    
    def get_full_name(self):
        """Return the full name of the teacher"""
        return f"{self.first_name} {self.middle_name or ''} {self.last_name}".strip()
    

    def get_absolute_url(self):
        return reverse('teacher_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if not self.employee_id and self.joining_date:
            # Generate employee ID based on organization type and year
            org_prefix = self.get_organization_prefix()
            year = self.joining_date.year
            
            last_teacher = Teacher.objects.filter(
                institution=self.institution,
                employee_id__startswith=f"{org_prefix}-{year}-"
            ).order_by('-employee_id').first()
            
            if last_teacher:
                try:
                    last_num = int(last_teacher.employee_id.split('-')[-1])
                    new_num = last_num + 1
                except ValueError:
                    new_num = 1
            else:
                new_num = 1
                
            self.employee_id = f"{org_prefix}-{year}-{new_num:04d}"
        
        super().save(*args, **kwargs)

    def get_organization_prefix(self):
        """Get prefix for employee ID based on organization type"""
        prefix_map = {
            'institute': 'INST',
            'school': 'SCH',
            'college': 'COL',
            'university': 'UNI',
            'coaching': 'COA',
            'other': 'TCH'
        }
        return prefix_map.get(self.organization_type, 'TCH')

    def get_teaching_experience(self):
        """Calculate total teaching experience including current role"""
        from datetime import date
        if self.joining_date:
            total_years = self.experience
            # Add experience from current institution
            if self.joining_date:
                current_experience = date.today().year - self.joining_date.year
                total_years += current_experience
            return total_years
        return self.experience

    def get_subjects_list(self):
        """Return comma-separated list of subjects"""
        return ", ".join([subject.name for subject in self.subjects.all()]) if self.subjects.exists() else "No subjects assigned"

    def is_senior_faculty(self):
        """Check if teacher is in senior position"""
        senior_designations = ['principal', 'vice_principal', 'headmaster', 'headmistress', 'professor']
        return self.designation in senior_designations

    def can_teach_grade(self, grade_level):
        """Check if teacher can teach specific grade level"""
        if not self.teaching_grade_levels:
            return False
        # Simple check - can be enhanced with more complex logic
        return grade_level in self.teaching_grade_levels
    
    def get_edit_url(self):
        """Get URL for editing teacher profile"""
        from django.urls import reverse
        return reverse('teachers:teacher_profile_edit')
    
    def get_profile_url(self):
        """Get URL for teacher profile"""
        from django.urls import reverse
        return reverse('teachers:teacher_profile')
    
    @classmethod
    def get_teachers_by_organization_type(cls, org_type):
        """Get teachers filtered by organization type"""
        return cls.objects.filter(organization_type=org_type, is_active=True)

    @classmethod
    def get_department_teachers(cls, department):
        """Get teachers by department"""
        return cls.objects.filter(department=department, is_active=True)

    @classmethod
    def get_teachers_by_designation(cls, designation):
        """Get teachers by designation"""
        return cls.objects.filter(designation=designation, is_active=True)

    @classmethod
    def get_statistics(cls, queryset=None):
        """Get comprehensive statistics for teachers"""
        if queryset is None:
            queryset = cls.objects.all()
        
        stats = {
            'total_count': queryset.count(),
            'active_count': queryset.filter(is_active=True).count(),
            'inactive_count': queryset.filter(is_active=False).count(),
        }
        
        # Experience statistics
        from django.db.models import Avg, Max, Min
        exp_stats = queryset.aggregate(
            avg_exp=Avg('experience'),
            max_exp=Max('experience'),
            min_exp=Min('experience')
        )
        stats.update(exp_stats)
        
        # Qualification distribution
        qualifications = {}
        for qual_code, qual_name in cls.QUALIFICATION_CHOICES:
            count = queryset.filter(qualification=qual_code).count()
            qualifications[qual_name] = count
        stats['qualifications'] = qualifications
        
        # Organization type distribution
        org_types = {}
        for org_code, org_name in cls.ORGANIZATION_TYPE_CHOICES:
            count = queryset.filter(organization_type=org_code).count()
            org_types[org_name] = count
        stats['organization_types'] = org_types
        
        # Department distribution
        departments = {}
        for dept_code, dept_name in cls.DEPARTMENT_CHOICES:
            count = queryset.filter(department=dept_code).count()
            departments[dept_name] = count
        stats['departments'] = departments
        
        # Designation distribution
        designations = {}
        for desig_code, desig_name in cls.DESIGNATION_CHOICES:
            count = queryset.filter(designation=desig_code).count()
            designations[desig_name] = count
        stats['designations'] = designations
        
        return stats

    def generate_teacher_id_card(self):
        """Generate teacher ID card (to be implemented)"""
        # This would use your QR generation and PDF rendering utilities
        pass

    class TeacherReport:
        """Nested class for generating various teacher reports"""
        
        @staticmethod
        def generate_department_wise_report(department=None):
            """Generate department-wise teacher report"""
            teachers = cls.objects.filter(is_active=True)
            if department:
                teachers = teachers.filter(department=department)
            return teachers
        
        @staticmethod
        def generate_qualification_wise_report():
            """Generate qualification-wise report"""
            return cls.objects.values('qualification').annotate(
                count=models.Count('id'),
                avg_experience=models.Avg('experience')
            )
        
        @staticmethod
        def generate_organization_type_report():
            """Generate organization type-wise report"""
            return cls.objects.values('organization_type').annotate(
                count=models.Count('id'),
                avg_salary=models.Avg('salary')
            )

# Additional models for teacher management

class TeacherAttendance(models.Model):
    """Model to track teacher attendance"""
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=(
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('leave', 'On Leave'),
        ('half_day', 'Half Day'),
    ))
    remarks = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['teacher', 'date']
        db_table = 'teachers_attendance'

class TeacherSalary(models.Model):
    """Model to track teacher salary payments"""
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    month = models.DateField()  # First day of the month
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ), default='pending')
    
    class Meta:
        unique_together = ['teacher', 'month']
        db_table = 'teachers_salary'