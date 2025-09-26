from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import Teacher,TeacherAttendance,TeacherSalary
from django.contrib.auth import get_user_model
from apps.organization.models import Institution
from apps.academics.models import Subject, Class

User = get_user_model()



class TeacherForm(forms.ModelForm):
    """Form for creating/updating Teacher instances with optional user account creation"""

    create_user_account = forms.BooleanField(
        required=False,
        initial=False,
        label="Create User Account",
        help_text="Create a system user account for this teacher"
    )

    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter password'}),
        help_text="Password for user account (if creating)"
    )

    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password'}),
        help_text="Confirm password"
    )

    class Meta:
        model = Teacher
        fields = [
            'first_name', 'middle_name', 'last_name', 'email', 'mobile',
            'dob', 'gender', 'blood_group', 'address', 'emergency_contact',
            'emergency_contact_name', 'qualification', 'specialization',
            'joining_date', 'experience', 'salary', 'is_class_teacher',
            'organization_type', 'department', 'designation', 'faculty_type',
            'teaching_grade_levels', 'subjects', 'class_teacher_of', 
            'department_head', 'photo', 'resume', 'degree_certificates', 'is_active'
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)

        # Filter subjects and classes by institution
        if self.institution:
            self.fields['subjects'].queryset = Subject.objects.filter(institution=self.institution)
            self.fields['class_teacher_of'].queryset = Class.objects.filter(institution=self.institution)
            self.fields['department_head'].queryset = Teacher.objects.filter(institution=self.institution)

        # Optional fields
        optional_fields = [
            'middle_name', 'blood_group', 'emergency_contact_name',
            'specialization', 'department', 'department_head',
            'teaching_grade_levels', 'photo', 'resume', 'degree_certificates'
        ]
        for field in optional_fields:
            self.fields[field].required = False

        # Add CSS classes and placeholders
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs['class'] = 'form-select select2-multiple'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            elif not isinstance(field.widget, (forms.CheckboxInput, forms.FileInput)):
                field.widget.attrs['class'] = 'form-control'
            if isinstance(field.widget, (forms.TextInput, forms.Textarea)) and not field.widget.attrs.get('placeholder'):
                field.widget.attrs['placeholder'] = f'Enter {field.label.lower()}'

        # Hide password fields initially
        for f in ['password', 'confirm_password']:
            field = self.fields.get(f)
            if field:
                field.widget.attrs['style'] = 'display:none;'

        # Disable user creation checkbox for existing teachers
        if self.instance and self.instance.pk:
            create_field = self.fields.get('create_user_account')
            if create_field:
                create_field.initial = False
                create_field.widget.attrs['disabled'] = True

    def clean(self):
        cleaned_data = super().clean()
        create_user_account = cleaned_data.get('create_user_account')
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if create_user_account:
            if not password:
                raise ValidationError("Password is required when creating user account")
            if password != confirm_password:
                raise ValidationError("Passwords do not match")

        # Email uniqueness check
        email = cleaned_data.get('email')
        if email:
            user_query = User.objects.filter(email=email)
            if self.instance and self.instance.user:
                user_query = user_query.exclude(pk=self.instance.user.pk)
            if user_query.exists():
                raise ValidationError("A user with this email already exists")

        # Class teacher validation
        is_class_teacher = cleaned_data.get('is_class_teacher')
        class_teacher_of = cleaned_data.get('class_teacher_of')
        if is_class_teacher and not class_teacher_of:
            raise ValidationError("Please select a class when assigning as class teacher")
        if not is_class_teacher and class_teacher_of:
            raise ValidationError("Cannot assign class without making teacher a class teacher")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.institution:
            instance.institution = self.institution
        if commit:
            instance.save()
            self.save_m2m()

            # Create user account if requested
            if self.cleaned_data.get('create_user_account') and not instance.user:
                self.create_user_account(instance)

        return instance

    def create_user_account(self, teacher):
        """Create a user account for the teacher"""
        email = self.cleaned_data['email']
        password = self.cleaned_data['password']

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=teacher.first_name,
            last_name=teacher.last_name,
            role=User.Role.TEACHER
        )
        teacher.user = user
        teacher.save()


class TeacherAttendanceForm(forms.ModelForm):
    """Form for teacher attendance"""
    
    class Meta:
        model = TeacherAttendance
        fields = ['teacher', 'date', 'status', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Enter remarks if any'}),
        }

    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        if self.institution:
            self.fields['teacher'].queryset = Teacher.objects.filter(
                institution=self.institution, is_active=True
            )
        
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        teacher = cleaned_data.get('teacher')
        date = cleaned_data.get('date')
        
        # Check for duplicate attendance
        if teacher and date:
            existing_attendance = TeacherAttendance.objects.filter(
                teacher=teacher, date=date
            )
            if self.instance and self.instance.pk:
                existing_attendance = existing_attendance.exclude(pk=self.instance.pk)
            
            if existing_attendance.exists():
                raise ValidationError(f"Attendance for {teacher} on {date} already exists")
        
        return cleaned_data


class TeacherSalaryForm(forms.ModelForm):
    """Form for teacher salary management"""
    
    class Meta:
        model = TeacherSalary
        fields = ['teacher', 'month', 'basic_salary', 'allowances', 'deductions', 'payment_date', 'payment_status']
        widgets = {
            'month': forms.DateInput(attrs={'type': 'month', 'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'allowances': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deductions': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        if self.institution:
            self.fields['teacher'].queryset = Teacher.objects.filter(
                institution=self.institution, is_active=True
            )
        
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        teacher = cleaned_data.get('teacher')
        month = cleaned_data.get('month')
        
        # Check for duplicate salary entry
        if teacher and month:
            existing_salary = TeacherSalary.objects.filter(
                teacher=teacher, month=month
            )
            if self.instance and self.instance.pk:
                existing_salary = existing_salary.exclude(pk=self.instance.pk)
            
            if existing_salary.exists():
                raise ValidationError(f"Salary for {teacher} for {month.strftime('%B %Y')} already exists")
        
        # Calculate net salary
        basic_salary = cleaned_data.get('basic_salary', 0) or 0
        allowances = cleaned_data.get('allowances', 0) or 0
        deductions = cleaned_data.get('deductions', 0) or 0
        
        cleaned_data['net_salary'] = basic_salary + allowances - deductions
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.net_salary = self.cleaned_data['net_salary']
        
        if commit:
            instance.save()
        
        return instance


class TeacherImportForm(forms.Form):
    """Form for importing teachers from CSV"""
    csv_file = forms.FileField(
        label='CSV File',
        help_text='Upload a CSV file with teacher data. Required columns: first_name, last_name, email, mobile, joining_date, designation, qualification'
    )
    create_user_accounts = forms.BooleanField(
        required=False,
        initial=True,
        help_text='Create user accounts for imported teachers'
    )
    default_password = forms.CharField(
        required=False,
        initial='teacher123',
        widget=forms.PasswordInput,
        help_text='Default password for user accounts'
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if csv_file:
            if not csv_file.name.endswith('.csv'):
                raise ValidationError("Please upload a CSV file")
        return csv_file


class TeacherFilterForm(forms.Form):
    """Form for filtering teachers"""
    search = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, email, ID...'
        })
    )
    organization_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Organization Types')] + list(Teacher.ORGANIZATION_TYPE_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    department = forms.ChoiceField(
        required=False,
        choices=[('', 'All Departments')] + list(Teacher.DEPARTMENT_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    designation = forms.ChoiceField(
        required=False,
        choices=[('', 'All Designations')] + list(Teacher.DESIGNATION_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    faculty_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Faculty Types')] + [
            ('regular', 'Regular'),
            ('visiting', 'Visiting'),
            ('guest', 'Guest'),
            ('contract', 'Contract'),
            ('part_time', 'Part Time'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Status'), ('active', 'Active'), ('inactive', 'Inactive')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_class_teacher = forms.ChoiceField(
        required=False,
        choices=[('', 'All'), ('true', 'Yes'), ('false', 'No')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    qualification = forms.ChoiceField(
        required=False,
        choices=[('', 'All Qualifications')] + list(Teacher.QUALIFICATION_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    gender = forms.ChoiceField(
        required=False,
        choices=[('', 'All Genders')] + list(Teacher.GENDER_CHOICES),
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class TeacherQuickAddForm(forms.ModelForm):
    """Form for quick addition of teachers (minimal fields)"""
    
    class Meta:
        model = Teacher
        fields = [
            'first_name', 'last_name', 'email', 'mobile', 
            'designation', 'qualification', 'joining_date'
        ]
        widgets = {
            'joining_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = f'Enter {field.label.lower()}'

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.institution:
            instance.institution = self.institution
            instance.organization_type = self.institution.institution_type
        
        if commit:
            instance.save()
        
        return instance