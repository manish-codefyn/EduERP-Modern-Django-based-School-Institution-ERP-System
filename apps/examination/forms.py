from django import forms
from .models import ExamType, Exam, ExamSubject, ExamResult
from apps.organization.models import Institution
from apps.academics.models import AcademicYear, Subject
from apps.students.models import Student
from apps.core.utils import get_user_institution

class ExamTypeForm(forms.ModelForm):
    class Meta:
        model = ExamType
        fields = ['name', 'code', 'description', 'is_active']  # remove 'institution'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        # Remove 'institution' from fields
        fields = ['exam_type', 'name', 'academic_year', 'start_date', 'end_date', 'is_published']
        widgets = {
            'exam_type': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'academic_year': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['exam_type'].queryset = ExamType.objects.filter(is_active=True)
        self.fields['academic_year'].queryset = AcademicYear.objects.filter(is_current=True)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("End date must be after start date")
        return cleaned_data
class ExamSubjectForm(forms.ModelForm):
    class Meta:
        model = ExamSubject
        fields = ['exam', 'subject', 'max_marks', 'pass_marks', 'exam_date', 'start_time', 'end_time']
        widgets = {
            'exam': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'max_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'pass_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'exam_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        # Pop the request from kwargs if it exists
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Example: filter subjects based on institution from request
        if self.request:
            institution = get_user_institution(self.request.user)
            self.fields['subject'].queryset = Subject.objects.filter(is_active=True, institution=institution)
        else:
            self.fields['subject'].queryset = Subject.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        max_marks = cleaned_data.get('max_marks')
        pass_marks = cleaned_data.get('pass_marks')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if max_marks and pass_marks and pass_marks > max_marks:
            raise forms.ValidationError("Pass marks cannot be greater than maximum marks")

        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError("End time must be after start time")

        return cleaned_data

    


class ExamResultForm(forms.ModelForm):
    class Meta:
        model = ExamResult
        fields = ['exam_subject', 'student', 'marks_obtained', 'remarks']
        widgets = {
            'exam_subject': forms.Select(attrs={'class': 'form-control'}),
            'student': forms.Select(attrs={'class': 'form-control'}),
            'marks_obtained': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Pop user from kwargs
        super().__init__(*args, **kwargs)
        
        if user:
            institution = get_user_institution(user)
            
            # Filter exam_subject by institution
            self.fields['exam_subject'].queryset = ExamSubject.objects.filter(
                exam__institution=institution
            ).select_related('exam', 'subject')
            
            # Filter students by institution
            self.fields['student'].queryset = Student.objects.filter(
                institution=institution
            ).select_related('user')

    def clean_marks_obtained(self):
        marks_obtained = self.cleaned_data.get('marks_obtained')
        exam_subject = self.cleaned_data.get('exam_subject')
        
        if marks_obtained is not None and exam_subject:
            if marks_obtained > exam_subject.max_marks:
                raise forms.ValidationError(
                    f"Marks obtained cannot exceed maximum marks ({exam_subject.max_marks})"
                )
            if marks_obtained < 0:
                raise forms.ValidationError("Marks obtained cannot be negative")
        
        return marks_obtained
