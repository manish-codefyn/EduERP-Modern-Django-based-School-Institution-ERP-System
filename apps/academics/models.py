import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


class AcademicYear(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'academics_academic_year'
        unique_together = ['institution', 'name']
    
    def __str__(self):
        return self.name

class Class(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    capacity = models.IntegerField(default=40)
    room_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'academics_class'
        unique_together = ['institution', 'code']
        verbose_name_plural = 'Classes'
    
    def __str__(self):
        return self.name

class Section(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=100)
    capacity = models.IntegerField(default=40)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'academics_section'
        unique_together = ['institution', 'class_name', 'name']
    
    def __str__(self):
        return f"{self.class_name} - {self.name}"
    
    
class House(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=50, blank=True, help_text="Optional color for identification (e.g. Red, Blue)")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'academics_house'
        ordering = ['name']

    def __str__(self):
        return self.name
    
    

class Subject(models.Model):
    # Subject type choices
    CORE = 'core'
    ELECTIVE = 'elective'
    SUBJECT_TYPE_CHOICES = [
        (CORE, 'Core Subject'),
        (ELECTIVE, 'Elective Subject'),
    ]
    
    # Difficulty level choices
    BASIC = 'basic'
    INTERMEDIATE = 'intermediate'
    ADVANCED = 'advanced'
    DIFFICULTY_LEVEL_CHOICES = [
        (BASIC, 'Basic'),
        (INTERMEDIATE, 'Intermediate'),
        (ADVANCED, 'Advanced'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    
    # New fields
    subject_type = models.CharField(
        max_length=10, 
        choices=SUBJECT_TYPE_CHOICES, 
        default=CORE,
        help_text="Whether this is a core required subject or an elective"
    )
    difficulty_level = models.CharField(
        max_length=12, 
        choices=DIFFICULTY_LEVEL_CHOICES, 
        default=BASIC,
        help_text="Difficulty level of the subject"
    )
    credits = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Number of credit hours this subject is worth"
    )
    prerequisites = models.ManyToManyField(
        'self', 
        symmetrical=False, 
        blank=True,
        help_text="Subjects that must be completed before taking this one"
    )
    department = models.ForeignKey(
        'organization.Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Department that offers this subject"
    )
    
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'academics_subject'
        unique_together = ['institution', 'code']
        ordering = ['code', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def is_elective(self):
        return self.subject_type == self.ELECTIVE
    
    def is_core(self):
        return self.subject_type == self.CORE
    

class Timetable(models.Model):
    DAY_CHOICES = (
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    period = models.IntegerField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey('teachers.Teacher', on_delete=models.CASCADE)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'academics_timetable'
        unique_together = ['institution', 'academic_year', 'class_name', 'section', 'day', 'period']
        ordering = ['day', 'period']
    
    def __str__(self):
        return f"{self.class_name} - {self.day} - Period {self.period}"