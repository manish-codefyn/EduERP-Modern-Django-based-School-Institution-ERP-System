# forms.py

from django import forms
from .models import (Staff,Department,Designation,Faculty,LeaveType,LeaveApplication,LeaveBalance,Payroll,HrAttendance)
from apps.core.utils import get_user_institution
from django.contrib.auth import get_user_model
from apps.organization.models import Institution
from apps.hr.models import Staff

User = get_user_model()

from django import forms
from .models import HrAttendance, Staff

class AttendanceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Filter staff by user's institution
        if self.request and hasattr(self.request.user, 'institution'):
            institution = self.request.user.institution
            self.fields['staff'].queryset = Staff.objects.filter(institution=institution, is_active=True)
        
        # Add Bootstrap classes to widgets
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput) or isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'date'})
            elif isinstance(field.widget, forms.TimeInput):
                field.widget.attrs.update({'class': 'form-control', 'type': 'time'})

    class Meta:
        model = HrAttendance
        fields = [
            'staff', 'date', 'check_in', 'check_out', 'status', 
            'hours_worked', 'remarks'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'check_in': forms.TimeInput(attrs={'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'type': 'time'}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'hours_worked': 'Hours Worked (auto-calculated)',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        staff = cleaned_data.get('staff')
        date = cleaned_data.get('date')
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')
        instance = self.instance
        
        # Check for duplicate attendance for same staff and date
        if staff and date:
            existing = HrAttendance.objects.filter(
                staff=staff, 
                date=date
            ).exclude(pk=instance.pk if instance else None)
            
            if existing.exists():
                raise forms.ValidationError(
                    f"Attendance record already exists for {staff} on {date}"
                )
        
        # Validate check-out time is after check-in time
        if check_in and check_out and check_out <= check_in:
            raise forms.ValidationError("Check-out time must be after check-in time")
        
        return cleaned_data


STATUS_CHOICES = [
    ('', 'All'),
    ('present', 'Present'),
    ('absent', 'Absent'),
    ('leave', 'On Leave'),
    ('holiday', 'Holiday'),
]

class AttendanceFilterForm(forms.Form):
    staff = forms.ModelChoiceField(
        queryset=Staff.objects.none(),
        required=False,
        label='Staff',
        empty_label="All Staff",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        label='Date From',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        label='Date To',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label='Status',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.request and hasattr(self.request.user, 'institution'):
            institution = self.request.user.institution
            self.fields['staff'].queryset = Staff.objects.filter(
                institution=institution, 
                is_active=True
            ).select_related('user')



# class AttendanceFilterForm(forms.Form):
#     staff = forms.ModelChoiceField(
#         queryset=Staff.objects.none(),
#         required=False,
#         empty_label="All Staff"
#     )
#     date_from = forms.DateField(
#         required=False,
#         widget=forms.DateInput(attrs={'type': 'date'})
#     )
#     date_to = forms.DateField(
#         required=False,
#         widget=forms.DateInput(attrs={'type': 'date'})
#     )
#     status = forms.ChoiceField(
#         choices=[('', 'All Status')] + list(HrAttendance._meta.get_field('status').choices),
#         required=False
#     )
    
#     def __init__(self, *args, **kwargs):
#         self.request = kwargs.pop('request', None)
#         super().__init__(*args, **kwargs)
        
#         if self.request and hasattr(self.request.user, 'institution'):
#             institution = self.request.user.institution
#             self.fields['staff'].queryset = Staff.objects.filter(
#                 institution=institution, 
#                 is_active=True
#             ).select_related('user')



class PayrollForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = [
            'staff', 'month', 'year', 'basic_salary', 'house_rent_allowance',
            'travel_allowance', 'medical_allowance', 'special_allowance',
            'performance_bonus', 'other_allowances', 'professional_tax',
            'provident_fund', 'income_tax', 'insurance', 'loan_deductions',
            'other_deductions', 'payment_date', 'payment_mode',
            'payment_reference', 'payment_status'
        ]
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'month': forms.Select(choices=[(i, f'{i} - {["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"][i-1]}') for i in range(1, 13)]),
            'year': forms.Select(choices=[(i, i) for i in range(2020, 2031)]),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Limit staff choices to current institution
        if self.request and hasattr(self.request.user, 'institution'):
            institution = self.request.user.institution
            self.fields['staff'].queryset = self.fields['staff'].queryset.filter(
                institution=institution, is_active=True
            )
        
        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            
        # Specific styling for numeric fields
        numeric_fields = [
            'basic_salary', 'house_rent_allowance', 'travel_allowance',
            'medical_allowance', 'special_allowance', 'performance_bonus',
            'other_allowances', 'professional_tax', 'provident_fund',
            'income_tax', 'insurance', 'loan_deductions', 'other_deductions'
        ]
        
        for field_name in numeric_fields:
            self.fields[field_name].widget.attrs['class'] += ' text-end'
            self.fields[field_name].widget.attrs['step'] = '0.01'
    
    def clean(self):
        cleaned_data = super().clean()
        staff = cleaned_data.get('staff')
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')
        
        if staff and month and year:
            # Check for duplicate payroll record
            queryset = Payroll.objects.filter(staff=staff, month=month, year=year)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError(
                    f"A payroll record for {staff} already exists for {month}/{year}."
                )
        
        return cleaned_data

class LeaveBalanceForm(forms.ModelForm):
    class Meta:
        model = LeaveBalance
        fields = ['staff', 'leave_type', 'year', 'total_allocated', 'carry_forward']
        widgets = {
            'year': forms.NumberInput(attrs={'min': 2000, 'max': 2100}),
            'total_allocated': forms.NumberInput(attrs={'min': 0}),
            'carry_forward': forms.NumberInput(attrs={'min': 0}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.request and hasattr(self.request, 'user'):
            institution = get_user_institution(self.request.user)
            if institution:
                # Filter staff and leave types by institution
                self.fields['staff'].queryset = self.fields['staff'].queryset.filter(institution=institution)
                self.fields['leave_type'].queryset = self.fields['leave_type'].queryset.filter(institution=institution)
    
    def clean(self):
        cleaned_data = super().clean()
        staff = cleaned_data.get('staff')
        leave_type = cleaned_data.get('leave_type')
        year = cleaned_data.get('year')
        
        # Check for unique constraint
        if staff and leave_type and year:
            if self.instance and self.instance.pk:
                # For update, exclude current instance
                if LeaveBalance.objects.filter(
                    staff=staff, 
                    leave_type=leave_type, 
                    year=year
                ).exclude(pk=self.instance.pk).exists():
                    raise forms.ValidationError(
                        "A leave balance record already exists for this staff, leave type, and year combination."
                    )
            else:
                # For create
                if LeaveBalance.objects.filter(
                    staff=staff, 
                    leave_type=leave_type, 
                    year=year
                ).exists():
                    raise forms.ValidationError(
                        "A leave balance record already exists for this staff, leave type, and year combination."
                    )
        
        return cleaned_data

class LeaveApplicationForm(forms.ModelForm):
    class Meta:
        model = LeaveApplication
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'supporting_document']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter reason for leave'}),
            'supporting_document': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.request and hasattr(self.request.user, 'staff'):
            # Filter leave types by institution and active status
            institution = self.request.user.staff.institution
            self.fields['leave_type'].queryset = LeaveType.objects.filter(
                institution=institution, 
                is_active=True
            )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError("End date cannot be before start date.")
            
            # Check if dates are in the past (for new applications)
            if not self.instance.pk and start_date < timezone.now().date():
                raise forms.ValidationError("Cannot apply for leave in the past.")
        
        return cleaned_data

class LeaveApplicationReviewForm(forms.ModelForm):
    class Meta:
        model = LeaveApplication
        fields = ['status', 'remarks']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter remarks or comments'}),
        }

class LeaveTypeForm(forms.ModelForm):
    class Meta:
        model = LeaveType
        fields = ['name', 'code', 'max_days', 'carry_forward', 
                 'max_carry_forward', 'requires_approval', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter leave type name'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter unique code'}),
            'max_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'max_carry_forward': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'carry_forward': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_approval': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field_name not in ['carry_forward', 'requires_approval', 'is_active']:
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if self.instance and self.instance.pk:
            if LeaveType.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("A leave type with this code already exists.")
        else:
            if LeaveType.objects.filter(code=code).exists():
                raise forms.ValidationError("A leave type with this code already exists.")
        return code


class FacultyForm(forms.ModelForm):
    class Meta:
        model = Faculty
        fields = [
            'staff', 'qualification', 'degree', 'specialization', 
            'year_of_graduation', 'university', 'subjects', 
            'total_experience', 'research_publications', 'is_class_teacher',
            'class_teacher_of', 'training_courses', 'conferences_attended',
            'awards', 'office_hours', 'office_location'
        ]
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-control'}),
            'qualification': forms.Select(attrs={'class': 'form-control'}),
            'degree': forms.TextInput(attrs={'class': 'form-control'}),
            'specialization': forms.Select(attrs={'class': 'form-control'}),
            'year_of_graduation': forms.NumberInput(attrs={'class': 'form-control'}),
            'university': forms.TextInput(attrs={'class': 'form-control'}),
            'subjects': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'total_experience': forms.NumberInput(attrs={'class': 'form-control'}),
            'research_publications': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_class_teacher': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'class_teacher_of': forms.Select(attrs={'class': 'form-control'}),
            'training_courses': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'conferences_attended': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'awards': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'office_hours': forms.TextInput(attrs={'class': 'form-control'}),
            'office_location': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # You can add custom initialization if needed


class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = [
            'user', 'employee_id', 'staff_type', 'department', 'designation',
            'reporting_manager', 'date_of_birth', 'gender', 'blood_group',
            'marital_status', 'personal_email', 'personal_phone',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relation', 'employment_type', 'joining_date',
            'contract_end_date', 'probation_end_date', 'resignation_date',
            'resignation_reason', 'salary', 'bank_account', 'bank_name',
            'ifsc_code', 'pan_number', 'aadhaar_number', 'photo', 'resume',
            'id_proof', 'address_proof', 'qualification_proof', 'is_active'
        ]
        widgets = {
            # Basic Information
            'user': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select User'
            }),
            'employee_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Employee ID'
            }),
            'staff_type': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select Staff Type'
            }),
            'department': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select Department'
            }),
            'designation': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select Designation'
            }),
            'reporting_manager': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select Reporting Manager'
            }),
            
            # Personal Information
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': 'Date of Birth'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select Gender'
            }),
            'blood_group': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select Blood Group'
            }),
            'marital_status': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select Marital Status'
            }),
            
            # Contact Information
            'personal_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Personal Email'
            }),
            'personal_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Personal Phone'
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Emergency Contact Name'
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Emergency Contact Phone'
            }),
            'emergency_contact_relation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Emergency Contact Relation'
            }),
            
            # Employment Details
            'employment_type': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select Employment Type'
            }),
            'joining_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': 'Joining Date'
            }),
            'contract_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': 'Contract End Date'
            }),
            'probation_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': 'Probation End Date'
            }),
            'resignation_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': 'Resignation Date'
            }),
            'resignation_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Resignation Reason',
                'rows': 3
            }),
            
            # Financial Information
            'salary': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Salary',
                'step': '0.01'
            }),
            'bank_account': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank Account Number'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank Name'
            }),
            'ifsc_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'IFSC Code'
            }),
            'pan_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'PAN Number'
            }),
            'aadhaar_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Aadhaar Number'
            }),
            
            # Documents
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'resume': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            }),
            'id_proof': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'address_proof': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'qualification_proof': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            
            # Status
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        # Extract institution from kwargs before calling super()
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        # Set required fields
        self.fields['joining_date'].required = True
        self.fields['employment_type'].required = True
        self.fields['salary'].required = True
        
        # Filter querysets based on institution if provided
        if self.institution:
            self.fields['department'].queryset = Department.objects.filter(institution=self.institution)
            self.fields['reporting_manager'].queryset = Staff.objects.filter(institution=self.institution)
            
            # Filter users based on institution membership
            # Adjust this based on your actual user-institution relationship
            if hasattr(User, 'institution_memberships'):
                # If users have a many-to-many relationship with institutions
                user_queryset = User.objects.filter(institution_memberships=self.institution)
            elif hasattr(User, 'profile') and hasattr(User.profile, 'institution'):
                # If users have a profile with institution foreign key
                user_queryset = User.objects.filter(profile__institution=self.institution)
            else:
                # Fallback: show all users (you might want to adjust this)
                user_queryset = User.objects.all()
            
            # For new staff: show only users not already linked as staff
            if not self.instance.pk:
                self.fields['user'].queryset = user_queryset.exclude(staff_profile__isnull=False)
            else:
                # For existing staff: allow their current user plus other available users
                self.fields['user'].queryset = user_queryset
        
        # Add help texts
        self.fields['employee_id'].help_text = "Leave blank to auto-generate"
        self.fields['photo'].help_text = "Accepted formats: JPG, PNG, GIF"
        self.fields['resume'].help_text = "Accepted formats: PDF, DOC, DOCX"
        self.fields['id_proof'].help_text = "Accepted formats: PDF, JPG, PNG"
        self.fields['address_proof'].help_text = "Accepted formats: PDF, JPG, PNG"
        self.fields['qualification_proof'].help_text = "Accepted formats: PDF, JPG, PNG"
        
        # Add custom labels if needed
        self.fields['user'].label = "System User"
        self.fields['personal_email'].label = "Personal Email Address"
        self.fields['personal_phone'].label = "Personal Phone Number"
        
        # Add custom validation attributes
        self.fields['personal_phone'].widget.attrs.update({
            'pattern': '[0-9]{10}',
            'title': 'Please enter a valid 10-digit phone number'
        })
        self.fields['emergency_contact_phone'].widget.attrs.update({
            'pattern': '[0-9]{10}',
            'title': 'Please enter a valid 10-digit phone number'
        })
        self.fields['aadhaar_number'].widget.attrs.update({
            'pattern': '[0-9]{12}',
            'title': 'Please enter a valid 12-digit Aadhaar number'
        })
        self.fields['pan_number'].widget.attrs.update({
            'pattern': '[A-Z]{5}[0-9]{4}[A-Z]{1}',
            'title': 'Please enter a valid PAN number (e.g., ABCDE1234F)'
        })
    
    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id')
        if employee_id and self.institution:
            # Check if employee_id is unique within the institution
            queryset = Staff.objects.filter(
                institution=self.institution,
                employee_id=employee_id
            )
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError("Employee ID must be unique within the institution.")
        return employee_id
    
    def clean_personal_email(self):
        email = self.cleaned_data.get('personal_email')
        if email:
            # Check if email is unique
            queryset = Staff.objects.filter(personal_email=email)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError("This email is already registered with another staff member.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        joining_date = cleaned_data.get('joining_date')
        resignation_date = cleaned_data.get('resignation_date')
        contract_end_date = cleaned_data.get('contract_end_date')
        probation_end_date = cleaned_data.get('probation_end_date')
        
        # Validate date logic
        if resignation_date and joining_date and resignation_date < joining_date:
            raise forms.ValidationError({
                'resignation_date': 'Resignation date cannot be before joining date.'
            })
        
        if contract_end_date and joining_date and contract_end_date < joining_date:
            raise forms.ValidationError({
                'contract_end_date': 'Contract end date cannot be before joining date.'
            })
        
        if probation_end_date and joining_date and probation_end_date < joining_date:
            raise forms.ValidationError({
                'probation_end_date': 'Probation end date cannot be before joining date.'
            })
        
        return cleaned_data
    
    
class StaffFilterForm(forms.Form):
    STAFF_STATUS_CHOICES = (
        ('', 'All Status'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )
    
    staff_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Staff.STAFF_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    designation = forms.ModelChoiceField(  # Add this field
        queryset=Designation.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    employment_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Staff.EMPLOYMENT_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=STAFF_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name or employee ID...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        if institution:
            self.fields['department'].queryset = Department.objects.filter(institution=institution)
            self.fields['designation'].queryset = Designation.objects.filter(institution=institution)  # Add this line


class DesignationForm(forms.ModelForm):
    class Meta:
        model = Designation
        fields = [
            'name', 'code', 'category', 'grade', 'description',
            'min_salary', 'max_salary', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter designation name'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter unique code'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'grade': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Add a brief description'
            }),
            'min_salary': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Minimum Salary'
            }),
            'max_salary': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Maximum Salary'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)

        # Make grade required only for teaching category
        self.fields['grade'].required = False

        # Optional: Add Bootstrap 5 classes dynamically to all fields if not set
        for field_name, field in self.fields.items():
            if field.widget.attrs.get('class') is None:
                if isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs['class'] = 'form-check-input'
                else:
                    field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        grade = cleaned_data.get('grade')
        min_salary = cleaned_data.get('min_salary')
        max_salary = cleaned_data.get('max_salary')

        # Validate grade for teaching positions
        if category == 'teaching' and not grade:
            self.add_error('grade', 'Grade is required for teaching positions.')

        # Validate salary range
        if min_salary and max_salary and max_salary <= min_salary:
            self.add_error('max_salary', 'Maximum salary must be greater than minimum salary.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set institution
        if self.institution:
            instance.institution = self.institution

        if commit:
            instance.save()

        return instance


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = [
            'name', 'custom_name', 'department_type', 'description',
            'head_of_department', 'email', 'phone', 'office_location'
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Enter department description...'
            }),
            'name': forms.Select(attrs={
                'class': 'form-select department-name-select',
                'onchange': 'toggleCustomNameField()'
            }),
            'custom_name': forms.TextInput(attrs={
                'class': 'form-control custom-name-field',
                'placeholder': 'Specify custom department name',
                'style': 'display: none;'  # Initially hidden
            }),
            'department_type': forms.Select(attrs={'class': 'form-select'}),
            'head_of_department': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'department@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1-234-567-8900'
            }),
            'office_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Building A, Room 101'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)

        # Make custom_name required only when 'other' is selected
        self.fields['custom_name'].required = False

        # Filter head_of_department to staff from the same institution
        if self.institution:
            self.fields['head_of_department'].queryset = self.fields['head_of_department'].queryset.filter(
                institution=self.institution
            )

        # Add Bootstrap styling to all remaining fields
        for field_name, field in self.fields.items():
            if not hasattr(field.widget, 'attrs'):
                field.widget.attrs = {}
            # Avoid overriding existing classes
            existing_classes = field.widget.attrs.get('class', '')
            if 'form-control' not in existing_classes and 'form-select' not in existing_classes:
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = f'{existing_classes} form-select'.strip()
                else:
                    field.widget.attrs['class'] = f'{existing_classes} form-control'.strip()

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        custom_name = cleaned_data.get('custom_name')

        # Validate custom_name logic
        if name == 'other' and not custom_name:
            self.add_error('custom_name', 'Custom name is required when "Other" is selected.')
        if name != 'other' and custom_name:
            self.add_error('custom_name', 'Custom name should only be provided when "Other" is selected.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Set institution
        if self.institution:
            instance.institution = self.institution

        # Generate and set code
        if not instance.code:
            base_code = instance.generate_code()
            instance.code = instance.make_unique_code(base_code)

        if commit:
            instance.save()

        return instance
