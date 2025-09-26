from django import forms
from .models import Class, Section, Timetable, AcademicYear,Subject

class AcademicYearForm(forms.ModelForm):
    class Meta:
        model = AcademicYear
        fields = ['name', 'start_date', 'end_date', 'is_current']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = [
            'name', 
            'code', 
            'description', 
            'is_active', 
            'subject_type', 
            'difficulty_level',
            'credits',
            'prerequisites',
            'department'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'prerequisites': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code.isalnum():
            raise forms.ValidationError("Code must be alphanumeric.")
        return code

class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['name', 'capacity', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Section A, Blue Group'}),
            'capacity': forms.NumberInput(attrs={'min': 1}),
        }
        labels = {
            'name': 'Section Name',
            'capacity': 'Student Capacity',
            'is_active': 'Is Active',
        }
    
    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        class_name = self.initial.get('class_name')
        
        if self.institution and class_name:
            qs = Section.objects.filter(
                name=name, 
                institution=self.institution,
                class_name_id=class_name
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
                
            if qs.exists():
                raise forms.ValidationError('A section with this name already exists in this class.')
                
        return name

class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = ['academic_year', 'class_name', 'section', 'day', 'period', 
                 'subject', 'teacher', 'start_time', 'end_time', 'room', 'is_active']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        if self.institution:
            # Filter querysets based on institution
            self.fields['class_name'].queryset = Class.objects.filter(institution=self.institution)
            self.fields['section'].queryset = Section.objects.filter(institution=self.institution)
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(institution=self.institution)
            # You'll need similar filters for subject and teacher once those models are implemented
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('End time must be after start time.')
        
        return cleaned_data
    
    
class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name', 'code', 'capacity', 'room_number', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'e.g., Grade 10, Form 4'
            }),
            'code': forms.TextInput(attrs={
                'placeholder': 'e.g., G10, F4'
            }),
            'capacity': forms.NumberInput(attrs={
                'min': 1
            }),
            'room_number': forms.TextInput(attrs={
                'placeholder': 'e.g., Room 101, Block A-12'
            }),
        }
        labels = {
            'name': 'Class Name',
            'code': 'Class Code',
            'capacity': 'Student Capacity',
            'room_number': 'Room Number',
            'is_active': 'Is Active',
        }
    
    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        
        # Check for uniqueness within the institution
        if self.institution:
            qs = Class.objects.filter(code=code, institution=self.institution)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
                
            if qs.exists():
                raise forms.ValidationError('A class with this code already exists in your institution.')
                
        return code
    
    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')
        if capacity < 1:
            raise forms.ValidationError('Capacity must be at least 1.')
        return capacity
    
