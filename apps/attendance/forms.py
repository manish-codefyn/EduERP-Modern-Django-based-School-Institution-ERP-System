from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from .models import Attendance, StaffAttendance
from apps.students.models import Student
from apps.hr.models import Staff
from apps.organization.models import Institution

User = get_user_model()


from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import Attendance
from apps.students.models import Student


class AttendanceForm(forms.ModelForm):
    """Form for marking student attendance"""

    class Meta:
        model = Attendance
        fields = ['student', 'date', 'status', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'student': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'student': _('Student'),
            'date': _('Date'),
            'status': _('Status'),
            'remarks': _('Remarks'),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Set initial date to today
        self.fields['date'].initial = timezone.now().date()

        # Default: no students
        self.fields['student'].queryset = Student.objects.none()

        if self.request and hasattr(self.request.user, 'profile') and self.request.user.profile.institution:
            institution = self.request.user.profile.institution

            # Base queryset → only active students
            students = Student.objects.filter(
                institution=institution,
                status="ACTIVE"
            )

            # Role-based filtering
            if getattr(self.request.user, "is_teacher", False):
                from apps.academics.models import Class
                teacher_classes = Class.objects.filter(
                    teacher__user=self.request.user
                ).values_list('class_id', flat=True)
                students = students.filter(current_class_id__in=teacher_classes)

            elif getattr(self.request.user, "is_student", False) or getattr(self.request.user, "is_parent", False):
                students = Student.objects.none()

            self.fields['student'].queryset = students
            self.fields['student'].empty_label = _('Select Student')

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        date = cleaned_data.get('date')
        user = self.request.user if self.request else None

        today = timezone.now().date()

        # Teachers cannot mark backdated attendance
        if user and getattr(user, "is_teacher", False):
            if date and date < today:
                raise forms.ValidationError(
                    _('Teachers are not allowed to mark backdated attendance.')
                )

        # Prevent duplicate attendance
        if student and date:
            exists = Attendance.objects.filter(
                student=student,
                date=date,
                institution=student.institution
            )
            if self.instance.pk:
                exists = exists.exclude(pk=self.instance.pk)

            if exists.exists():
                raise forms.ValidationError(
                    _('Attendance for this student has already been marked on the selected date.')
                )

        return cleaned_data


class StaffAttendanceForm(forms.ModelForm):
    """Form for marking staff attendance"""
    
    class Meta:
        model = StaffAttendance
        fields = ['staff', 'date', 'status', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'staff': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'staff': _('Staff Member'),
            'date': _('Date'),
            'status': _('Status'),
            'remarks': _('Remarks'),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        self.fields['date'].initial = timezone.now().date()
        
        if self.request and hasattr(self.request.user, 'profile') and self.request.user.profile.institution:
            institution = self.request.user.profile.institution
            
            staff_members = Staff.objects.filter(
                institution=institution,
                is_active=True
            )
            
            if self.request.user.role == User.Role.HR:
                pass  # HR can mark all
            elif self.request.user.is_teacher:
                staff_members = staff_members.filter(user=self.request.user)
            else:
                staff_members = Staff.objects.none()
            
            self.fields['staff'].queryset = staff_members
            self.fields['staff'].empty_label = _('Select Staff Member')
        else:
            self.fields['staff'].queryset = Staff.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        staff = cleaned_data.get('staff')
        date = cleaned_data.get('date')

        # Restrict backdated marking
        if self.request and self.request.user.is_teacher:
            today = timezone.now().date()
            if date and date < today:
                raise forms.ValidationError(
                    _('Teachers cannot mark backdated staff attendance.')
                )
        
        if staff and date:
            if StaffAttendance.objects.filter(
                staff=staff,
                date=date,
                institution=staff.institution
            ).exists():
                if not self.instance.pk:
                    raise forms.ValidationError(
                        _('Attendance for this staff member has already been marked on the selected date.')
                    )
        
        return cleaned_data


class BulkAttendanceForm(forms.Form):
    """Form for bulk attendance marking"""
    
    date = forms.DateField(
        label=_('Date'),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now().date
    )
    
    class_id = forms.ModelChoiceField(
        label=_('Class'),
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    section_id = forms.ModelChoiceField(
        label=_('Section'),
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.request and hasattr(self.request.user, 'profile') and self.request.user.profile.institution:
            institution = self.request.user.profile.institution
            
            from apps.academics.models import Class, Section
            if self.request.user.is_teacher:
                from apps.academics.models import ClassSubject
                teacher_classes = ClassSubject.objects.filter(
                    teacher__user=self.request.user
                ).values_list('class_id', flat=True)
                self.fields['class_id'].queryset = Class.objects.filter(
                    institution=institution,
                    id__in=teacher_classes,
                    is_active=True
                )
            else:
                self.fields['class_id'].queryset = Class.objects.filter(
                    institution=institution,
                    is_active=True
                )
            
            self.fields['section_id'].queryset = Section.objects.none()
        else:
            from apps.academics.models import Class, Section
            self.fields['class_id'].queryset = Class.objects.none()
            self.fields['section_id'].queryset = Section.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')

        # Restrict teachers from backdated marking
        if self.request and self.request.user.is_teacher:
            today = timezone.now().date()
            if date and date < today:
                raise forms.ValidationError(
                    _('Teachers cannot mark bulk attendance for past dates.')
                )
        return cleaned_data


class BulkStaffAttendanceForm(forms.Form):
    """Form for bulk staff attendance marking"""
    
    date = forms.DateField(
        label=_('Date'),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now().date
    )
    
    department_id = forms.ModelChoiceField(
        label=_('Department'),
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        empty_label=_('All Departments')
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.request and hasattr(self.request.user, 'profile') and self.request.user.profile.institution:
            institution = self.request.user.profile.institution
            
            from apps.hr.models import Department
            if self.request.user.role == User.Role.HR or self.request.user.is_superadmin or self.request.user.is_institution_admin:
                self.fields['department_id'].queryset = Department.objects.filter(
                    institution=institution,
                    is_active=True
                )
            else:
                self.fields['department_id'].queryset = Department.objects.none()
        else:
            from apps.hr.models import Department
            self.fields['department_id'].queryset = Department.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')

        # Restrict teachers or non-HR from backdated bulk marking
        if self.request and self.request.user.is_teacher:
            today = timezone.now().date()
            if date and date < today:
                raise forms.ValidationError(
                    _('Teachers cannot mark bulk staff attendance for past dates.')
                )
        return cleaned_data


class AttendanceReportForm(forms.Form):
    """Form for generating attendance reports"""
    
    REPORT_TYPE_CHOICES = (
        ('student', _('Student Attendance')),
        ('staff', _('Staff Attendance')),
    )
    
    report_type = forms.ChoiceField(
        label=_('Report Type'),
        choices=REPORT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='student'
    )
    
    start_date = forms.DateField(
        label=_('Start Date'),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    
    end_date = forms.DateField(
        label=_('End Date'),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    
    class_id = forms.ModelChoiceField(
        label=_('Class'),
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    
    department_id = forms.ModelChoiceField(
        label=_('Department'),
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        today = timezone.now().date()
        first_day = today.replace(day=1)
        self.fields['start_date'].initial = first_day
        self.fields['end_date'].initial = today
        
        if self.request and hasattr(self.request.user, 'profile') and self.request.user.profile.institution:
            institution = self.request.user.profile.institution
            
            from apps.academics.models import Class
            from apps.hr.models import Department
            
            if self.request.user.has_permission('students', 'view'):
                self.fields['class_id'].queryset = Class.objects.filter(
                    institution=institution,
                    is_active=True
                )
            else:
                self.fields['class_id'].queryset = Class.objects.none()
            
            if self.request.user.has_permission('hr', 'view'):
                self.fields['department_id'].queryset = Department.objects.filter(
                    institution=institution,
                    is_active=True
                )
            else:
                self.fields['department_id'].queryset = Department.objects.none()
        else:
            from apps.academics.models import Class
            from apps.hr.models import Department
            self.fields['class_id'].queryset = Class.objects.none()
            self.fields['department_id'].queryset = Department.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError(
                    _('Start date cannot be after end date.')
                )
            if (end_date - start_date).days > 365:
                raise forms.ValidationError(
                    _('Report range cannot exceed 1 year.')
                )
        return cleaned_data


class AttendanceFilterForm(forms.Form):
    """Form for filtering attendance records"""
    
    date = forms.DateField(
        label=_('Date'),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    
    status = forms.ChoiceField(
        label=_('Status'),
        choices=[('', _('All Statuses'))] + list(Attendance.STATUS_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = timezone.now().date()


class StaffAttendanceFilterForm(forms.Form):
    """Form for filtering staff attendance records"""
    
    date = forms.DateField(
        label=_('Date'),
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    
    status = forms.ChoiceField(
        label=_('Status'),
        choices=[('', _('All Statuses'))] + list(StaffAttendance.STATUS_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    
    department_id = forms.ModelChoiceField(
        label=_('Department'),
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        empty_label=_('All Departments')
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = timezone.now().date()
        
        if self.request and hasattr(self.request.user, 'profile') and self.request.user.profile.institution:
            institution = self.request.user.profile.institution
            from apps.hr.models import Department
            self.fields['department_id'].queryset = Department.objects.filter(
                institution=institution,
                is_active=True
            )
        else:
            from apps.hr.models import Department
            self.fields['department_id'].queryset = Department.objects.none()
