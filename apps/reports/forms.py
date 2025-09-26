from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from apps.academics.models import Class, Section, AcademicYear,Subject
from django.db.models import Q
from django import forms
from apps.attendance.models import Attendance
from apps.finance.models import Payment,FeeStructure
from apps.students.models import Student


class AcademicFilterForm(forms.Form):
    student_class = forms.ModelChoiceField(
        queryset=Class.objects.none(), 
        required=False, 
        label="Class", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.none(), 
        required=False, 
        label="Section", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.none(), 
        required=False, 
        label="Academic Year", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(), 
        required=False, 
        label="Subject", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
   
    min_marks = forms.IntegerField(
        required=False,
        label="Minimum Marks",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'})
    )
    max_marks = forms.IntegerField(
        required=False,
        label="Maximum Marks",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'})
    )

class AcademicExportForm(forms.Form):
    export_format = forms.ChoiceField(
        choices=[
            ('csv', 'CSV'),
            ('excel', 'Excel'),
            ('pdf', 'PDF')
        ],
        required=True,
        label="Export Format",
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class FinancialFilterForm(forms.Form):
    start_date = forms.DateField(
        required=False, 
        label="Start Date", 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=False, 
        label="End Date", 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(), 
        required=False, 
        label="Student", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    student_class = forms.ModelChoiceField(
        queryset=Class.objects.none(), 
        required=False, 
        label="Class", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.none(), 
        required=False, 
        label="Academic Year", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    fee_type = forms.ModelChoiceField(
        queryset=FeeStructure.objects.none(), 
        required=False, 
        label="Fee Type", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    payment_mode = forms.ChoiceField(
        choices=Payment.MODE_CHOICES,
        required=False,
        label="Payment Mode",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=Payment.STATUS_CHOICES,
        required=False,
        label="Status",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class FinancialExportForm(forms.Form):
    export_format = forms.ChoiceField(
        choices=[
            ('csv', 'CSV'),
            ('excel', 'Excel'),
            ('pdf', 'PDF')
        ],
        required=True,
        label="Export Format",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    include_columns = forms.MultipleChoiceField(
        choices=[
            ('payment_number', 'Payment Number'),
            ('student', 'Student Name'),
            ('admission_number', 'Admission Number'),
            ('current_class', 'Class'),
            ('section', 'Section'),
            ('invoice_number', 'Invoice Number'),
            ('amount', 'Total Amount'),
            ('amount_paid', 'Amount Paid'),
            ('balance', 'Balance'),
            ('payment_mode', 'Payment Mode'),
            ('payment_date', 'Payment Date'),
            ('reference_number', 'Reference Number'),
            ('status', 'Status'),
            ('academic_year', 'Academic Year'),
            ('remarks', 'Remarks'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        initial=['payment_number', 'student', 'amount', 'amount_paid', 'payment_mode', 'payment_date', 'status']
    )


STATUS_CHOICES = [
    ('', 'Any'),
    ('PRESENT', 'Present'),
    ('ABSENT', 'Absent'),
    ('LEAVE', 'Leave'),
]
class AttendanceFilterForm(forms.Form):
    student_class = forms.ModelChoiceField(queryset=Class.objects.none(), required=False, label="Class", widget=forms.Select(attrs={'class':'form-select'}))
    section = forms.ModelChoiceField(queryset=Section.objects.none(), required=False, label="Section", widget=forms.Select(attrs={'class':'form-select'}))
    academic_year = forms.ModelChoiceField(queryset=AcademicYear.objects.none(), required=False, label="Academic Year", widget=forms.Select(attrs={'class':'form-select'}))
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False, label="Status", widget=forms.Select(attrs={'class':'form-select'}))
    start_date = forms.DateField(required=False, label="Start Date", widget=forms.DateInput(attrs={'type':'date','class':'form-control'}))
    end_date = forms.DateField(required=False, label="End Date", widget=forms.DateInput(attrs={'type':'date','class':'form-control'}))


class AttendanceExportForm(forms.Form):
    # Export format selection
    export_format = forms.ChoiceField(
        choices=[
            ('csv', 'CSV'),
            ('excel', 'Excel'),
            ('pdf', 'PDF')
        ],
        required=True,
        label="Export Format",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Filter fields (same as AttendanceFilterForm but with export-specific options)
    student_class = forms.ModelChoiceField(
        queryset=Class.objects.none(), 
        required=False, 
        label="Class", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.none(), 
        required=False, 
        label="Section", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.none(), 
        required=False, 
        label="Academic Year", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=Attendance.STATUS_CHOICES, 
        required=False, 
        label="Status", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    start_date = forms.DateField(
        required=False, 
        label="Start Date", 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=False, 
        label="End Date", 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    # Column selection for export
    COLUMN_CHOICES = [
        ('student', 'Student Name'),
        ('student_id', 'Student ID'),
        ('class', 'Class'),
        ('section', 'Section'),
        ('date', 'Date'),
        ('status', 'Status'),
        ('remarks', 'Remarks'),
        ('marked_by', 'Marked By'),
        ('created_at', 'Created At'),
    ]
    
    include_columns = forms.MultipleChoiceField(
        choices=COLUMN_CHOICES,
        required=False,
        label="Include Columns",
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        initial=[choice[0] for choice in COLUMN_CHOICES]  # Select all by default
    )
    
    # Additional export options
    include_header = forms.BooleanField(
        required=False, 
        initial=True,
        label="Include Column Headers",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    group_by_class = forms.BooleanField(
        required=False, 
        initial=False,
        label="Group by Class",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        # Set querysets based on institution
        if institution:
            self.fields['student_class'].queryset = Class.objects.filter(institution=institution)
            self.fields['section'].queryset = Section.objects.filter(institution=institution)
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(institution=institution)