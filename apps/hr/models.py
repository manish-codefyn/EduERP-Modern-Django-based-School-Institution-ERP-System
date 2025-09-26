import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.core.exceptions import ValidationError
import uuid
import re

class Department(models.Model):
    DEPARTMENT_TYPE_CHOICES = (
        ('academic', 'Academic'),
        ('administrative', 'Administrative'),
        ('support', 'Support'),
        ('research', 'Research'),
    )
    
    DEPARTMENT_NAME_CHOICES = (
        # Academic Departments
        ('computer_science', 'Computer Science Department'),
        ('mathematics', 'Mathematics Department'),
        ('physics', 'Physics Department'),
        ('chemistry', 'Chemistry Department'),
        ('biology', 'Biology Department'),
        ('english', 'English Department'),
        ('history', 'History Department'),
        ('economics', 'Economics Department'),
        ('business', 'Business Administration Department'),
        ('engineering', 'Engineering Department'),
        
        # Administrative Departments
        ('hr', 'Human Resources Department'),
        ('finance', 'Finance Department'),
        ('admissions', 'Admissions Department'),
        ('registrar', 'Registrar\'s Office'),
        ('student_affairs', 'Student Affairs Department'),
        ('academic_affairs', 'Academic Affairs Department'),
        ('administration', 'Administration Office'),
        ('facilities', 'Facilities Management Department'),
        
        # Support Departments
        ('it_support', 'IT Support Department'),
        ('library', 'Library Services Department'),
        ('maintenance', 'Maintenance Department'),
        ('counseling', 'Counseling Department'),
        ('career_services', 'Career Services Department'),
        ('health_services', 'Health Services Department'),
        ('security', 'Security Department'),
        
        # Research Departments
        ('rnd', 'Research and Development Department'),
        ('innovation', 'Innovation Center'),
        ('graduate_studies', 'Graduate Studies Department'),
        ('scientific_research', 'Scientific Research Department'),
        ('applied_research', 'Applied Research Department'),
        
        # Other
        ('other', 'Other (specify)'),
    )
    
    # Mapping for auto-generated codes based on department name
    DEPARTMENT_CODE_MAP = {
        'computer_science': 'CS',
        'mathematics': 'MATH',
        'physics': 'PHY',
        'chemistry': 'CHEM',
        'biology': 'BIO',
        'english': 'ENG',
        'history': 'HIST',
        'economics': 'ECON',
        'business': 'BUS',
        'engineering': 'ENG',
        'hr': 'HR',
        'finance': 'FIN',
        'admissions': 'ADM',
        'registrar': 'REG',
        'student_affairs': 'SA',
        'academic_affairs': 'AA',
        'administration': 'ADMIN',
        'facilities': 'FAC',
        'it_support': 'IT',
        'library': 'LIB',
        'maintenance': 'MAINT',
        'counseling': 'COUN',
        'career_services': 'CAREER',
        'health_services': 'HEALTH',
        'security': 'SEC',
        'rnd': 'RND',
        'innovation': 'INNOV',
        'graduate_studies': 'GRAD',
        'scientific_research': 'SCI',
        'applied_research': 'APP',
    }
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, choices=DEPARTMENT_NAME_CHOICES)
    custom_name = models.CharField(max_length=100, blank=True, help_text="Required if 'Other' is selected")
    code = models.CharField(max_length=20, blank=True, help_text="Auto-generated code based on department name")
    department_type = models.CharField(max_length=20, choices=DEPARTMENT_TYPE_CHOICES, default='academic')
    description = models.TextField(blank=True)
    head_of_department = models.ForeignKey('Staff', on_delete=models.SET_NULL, null=True, blank=True, related_name="headed_departments")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    office_location = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_department'
        unique_together = ['institution', 'code']
    
    def __str__(self):
        if self.name == 'other' and self.custom_name:
            return self.custom_name
        return self.get_name_display()
    
    def generate_code(self, name_choice=None):
        """
        Generate a department code based on the department name
        """
        if not name_choice:
            name_choice = self.name
        
        # If it's a custom department, generate code from custom name
        if name_choice == 'other' and self.custom_name:
            # Extract first letters of each word, max 4 characters
            words = self.custom_name.split()
            if len(words) == 1:
                # Single word: take first 4 characters
                code = words[0][:4].upper()
            else:
                # Multiple words: take first letter of each word, max 4 letters
                code = ''.join(word[0] for word in words[:4]).upper()
            return code
        
        # Use predefined code mapping
        if name_choice in self.DEPARTMENT_CODE_MAP:
            return self.DEPARTMENT_CODE_MAP[name_choice]
        
        return 'DEPT'  # Default fallback
    
    def make_unique_code(self, base_code):
        """
        Make the code unique within the institution by appending numbers if needed
        """
        if not self.code:
            return base_code
        
        # Check if code already exists
        existing_codes = Department.objects.filter(
            institution=self.institution,
            code__startswith=base_code
        ).exclude(pk=self.pk).values_list('code', flat=True)
        
        if not existing_codes:
            return base_code
        
        # Find the next available number
        counter = 1
        while True:
            new_code = f"{base_code}{counter}"
            if new_code not in existing_codes:
                return new_code
            counter += 1
    
    
    def save(self, *args, **kwargs):
        # Generate code if not set
        if not self.code:
            base_code = self.generate_code()
            self.code = self.make_unique_code(base_code)
        
        # Ensure custom_name is cleared if not "other"
        if self.name != 'other':
            self.custom_name = ''
        
        super().save(*args, **kwargs)


class Designation(models.Model):
    CATEGORY_CHOICES = (
        ('teaching', 'Teaching'),
        ('non_teaching', 'Non-Teaching'),
        ('administrative', 'Administrative'),
    )
    
    GRADE_CHOICES = (
        ('professor', 'Professor'),
        ('associate_professor', 'Associate Professor'),
        ('assistant_professor', 'Assistant Professor'),
        ('lecturer', 'Lecturer'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    head = models.ForeignKey('Staff', null=True, blank=True, on_delete=models.SET_NULL, related_name='headed_designations')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='non_teaching')
    grade = models.CharField(max_length=30, choices=GRADE_CHOICES, blank=True)
    description = models.TextField(blank=True)
    min_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_designation'
        unique_together = ['institution', 'code']
    
    def __str__(self):
        return self.name


class Staff(models.Model):
    EMPLOYMENT_TYPE_CHOICES = (
        ('permanent', 'Permanent'),
        ('contract', 'Contract'),
        ('temporary', 'Temporary'),
        ('probation', 'Probation'),
        ('visiting', 'Visiting'),
    )
    
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )
    
    BLOOD_GROUP_CHOICES = (
        ('a+', 'A+'),
        ('a-', 'A-'),
        ('b+', 'B+'),
        ('b-', 'B-'),
        ('ab+', 'AB+'),
        ('ab-', 'AB-'),
        ('o+', 'O+'),
        ('o-', 'O-'),
    )
    
    STAFF_TYPE_CHOICES = (
        ('teaching', 'Teaching Staff'),
        ('non_teaching', 'Non-Teaching Staff'),
        ('administrative', 'Administrative Staff'),
        ('support', 'Support Staff'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profile')
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=50)
    staff_type = models.CharField(max_length=20, choices=STAFF_TYPE_CHOICES)  # Added staff type
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE)
    reporting_manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Personal Information
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True)
    marital_status = models.CharField(max_length=10, choices=(
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ), blank=True)
    
    # Contact Information
    personal_email = models.EmailField(blank=True)
    personal_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True)
    
    # Employment Details
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES)
    joining_date = models.DateField()
    contract_end_date = models.DateField(null=True, blank=True)
    probation_end_date = models.DateField(null=True, blank=True)
    resignation_date = models.DateField(null=True, blank=True)
    resignation_reason = models.TextField(blank=True)
    
    # Financial Information
    salary = models.DecimalField(max_digits=12, decimal_places=2)
    bank_account = models.CharField(max_length=50, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    pan_number = models.CharField(max_length=20, blank=True)
    aadhaar_number = models.CharField(max_length=20, blank=True)
    
    # Documents
    photo = models.ImageField(upload_to='staff_photos/', blank=True, null=True)
    resume = models.FileField(upload_to='staff_resumes/', blank=True, null=True)
    id_proof = models.FileField(upload_to='staff_id_proofs/', blank=True, null=True)
    address_proof = models.FileField(upload_to='staff_address_proofs/', blank=True, null=True)
    qualification_proof = models.FileField(upload_to='staff_qualification_proofs/', blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_staff'
        unique_together = ['institution', 'employee_id']  # Made employee_id unique per institution
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"
    
    @property
    def experience(self):
        if self.joining_date:
            today = timezone.now().date()
            if self.resignation_date:
                end_date = self.resignation_date
            else:
                end_date = today
            
            delta = end_date - self.joining_date
            years = delta.days // 365
            months = (delta.days % 365) // 30
            return f"{years} years, {months} months"
        return "N/A"
    
    def save(self, *args, **kwargs):
        if not self.employee_id:
            year = self.joining_date.year
            last_staff = Staff.objects.filter(
                institution=self.institution,
                employee_id__startswith=f"EMP-{year}-"
            ).order_by('-employee_id').first()
            
            if last_staff:
                last_num = int(last_staff.employee_id.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
                
            self.employee_id = f"EMP-{year}-{new_num:04d}"
        
        super().save(*args, **kwargs)



class Faculty(models.Model):
    QUALIFICATION_CHOICES = (
        ('phd', 'Ph.D.'),
        ('masters', 'Masters'),
        ('bachelors', 'Bachelors'),
        ('diploma', 'Diploma'),
        ('other', 'Other'),
    )
    
    SPECIALIZATION_CHOICES = (
        ('computer_science', 'Computer Science'),
        ('mathematics', 'Mathematics'),
        ('physics', 'Physics'),
        ('chemistry', 'Chemistry'),
        ('biology', 'Biology'),
        ('english', 'English'),
        ('history', 'History'),
        ('economics', 'Economics'),
        ('commerce', 'Commerce'),
        ('physical_education', 'Physical Education'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.OneToOneField(Staff, on_delete=models.CASCADE, related_name='faculty_profile')
    
    # Academic Information
    qualification = models.CharField(max_length=20, choices=QUALIFICATION_CHOICES)
    degree = models.CharField(max_length=100)
    specialization = models.CharField(max_length=50, choices=SPECIALIZATION_CHOICES)
    year_of_graduation = models.IntegerField()
    university = models.CharField(max_length=200)
    
    # Teaching Information
    subjects = models.ManyToManyField('academics.Subject', blank=True, related_name='faculty_members')
    total_experience = models.IntegerField(help_text="Total teaching experience in years")
    research_publications = models.IntegerField(default=0)
    is_class_teacher = models.BooleanField(default=False)
    class_teacher_of = models.ForeignKey('academics.Class', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Professional Development
    training_courses = models.TextField(blank=True)
    conferences_attended = models.TextField(blank=True)
    awards = models.TextField(blank=True)
    
    # Availability
    office_hours = models.CharField(max_length=100, blank=True)
    office_location = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_faculty'
        verbose_name_plural = 'Faculty'
    
    def __str__(self):
        return f"Prof. {self.staff.user.get_full_name()}"
    
    @property
    def current_designation(self):
        return self.staff.designation.name


class LeaveType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    max_days = models.IntegerField()
    carry_forward = models.BooleanField(default=False)
    max_carry_forward = models.IntegerField(default=0)
    requires_approval = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_leave_type'
        unique_together = ['institution', 'code']
    
    def __str__(self):
        return self.name

class LeaveApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    
    # Supporting documents
    supporting_document = models.FileField(upload_to='leave_documents/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_leave_application'
    
    def __str__(self):
        return f"{self.staff} - {self.leave_type} ({self.start_date} to {self.end_date})"
    
    def save(self, *args, **kwargs):
        # Calculate total days
        self.total_days = (self.end_date - self.start_date).days + 1
        super().save(*args, **kwargs)

class LeaveBalance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField()
    total_allocated = models.IntegerField()
    total_used = models.IntegerField(default=0)
    carry_forward = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_leave_balance'
        unique_together = ['staff', 'leave_type', 'year']
    
    def __str__(self):
        return f"{self.staff} - {self.leave_type} ({self.year})"
    
    @property
    def balance(self):
        return self.total_allocated + self.carry_forward - self.total_used

class Payroll(models.Model):

    PAYMENT_STATUS_PENDING = 'pending'
    PAYMENT_STATUS_PAID = 'paid'
    PAYMENT_STATUS_FAILED = 'failed'

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PENDING, 'Pending'),
        (PAYMENT_STATUS_PAID, 'Paid'),
        (PAYMENT_STATUS_FAILED, 'Failed'),
    ]
    # Payment Mode Choices
    PAYMENT_MODE_BANK_TRANSFER = 'bank_transfer'
    PAYMENT_MODE_CHEQUE = 'cheque'
    PAYMENT_MODE_CASH = 'cash'

    PAYMENT_MODE_CHOICES = [
        (PAYMENT_MODE_BANK_TRANSFER, 'Bank Transfer'),
        (PAYMENT_MODE_CHEQUE, 'Cheque'),
        (PAYMENT_MODE_CASH, 'Cash'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    month = models.IntegerField()  # 1-12
    year = models.IntegerField()
    
    # Earnings
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    house_rent_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    travel_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    special_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    performance_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Deductions
    professional_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    provident_fund = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    income_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    insurance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    loan_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Totals
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Payment details
    payment_date = models.DateField(null=True, blank=True)
    payment_mode = models.CharField(
        max_length=20,
        choices=PAYMENT_MODE_CHOICES,
        default=PAYMENT_MODE_BANK_TRANSFER
    )
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_STATUS_PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_payroll'
        unique_together = ['institution', 'staff', 'month', 'year']
    
    def __str__(self):
        return f"{self.staff} - {self.month}/{self.year}"
    
    def save(self, *args, **kwargs):
        # Calculate totals
        self.total_earnings = (
            self.basic_salary + 
            self.house_rent_allowance + 
            self.travel_allowance + 
            self.medical_allowance + 
            self.special_allowance + 
            self.performance_bonus + 
            self.other_allowances
        )
        
        self.total_deductions = (
            self.professional_tax + 
            self.provident_fund + 
            self.income_tax + 
            self.insurance + 
            self.loan_deductions + 
            self.other_deductions
        )
    
        self.net_salary = self.total_earnings - self.total_deductions
        super().save(*args, **kwargs)

class HrAttendance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=(
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('half_day', 'Half Day'),
        ('leave', 'On Leave'),
        ('holiday', 'Holiday'),
        ('weekend', 'Weekend'),
    ), default='present')
    hours_worked = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    remarks = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_attendance'
        unique_together = ['staff', 'date']
    
    def __str__(self):
        return f"{self.staff} - {self.date} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Calculate hours worked if check_in and check_out are provided
        if self.check_in and self.check_out:
            from datetime import datetime
            check_in_dt = datetime.combine(self.date, self.check_in)
            check_out_dt = datetime.combine(self.date, self.check_out)
            delta = check_out_dt - check_in_dt
            self.hours_worked = round(delta.total_seconds() / 3600, 2)
        
        super().save(*args, **kwargs)