from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from .models import (
    Student, Guardian, StudentMedicalInfo, StudentAddress, 
    StudentDocument, StudentTransport, StudentHostel, StudentHistory,StudentIdentification
# Common validators
)
from apps.core.forms import BaseForm,BaseSearchForm
from apps.academics.models import Class, Section, AcademicYear
from django.db.models import Q
from .models import Student
phone_regex = RegexValidator(
    regex=r"^\+?1?\d{9,15}$",
    message=_("Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."),
)

# -------------------- Student Form --------------------


STATUS_CHOICES = [
    ('ACTIVE', 'Active'),
    ('INACTIVE', 'Inactive')
]

GENDER_CHOICES = [
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other')
]

class StudentExportForm(forms.Form):
    student_class = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        required=False,
        label="Class",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.all(),
        required=False,
        label="Section",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        required=False,
        label="Academic Year",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'Any')] + list(Student.STATUS_CHOICES),
        required=False,
        label="Status",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    gender = forms.ChoiceField(
        choices=[('', 'Any')] + list(Student.GENDER_CHOICES),
        required=False,
        label="Gender",
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class StudentForm(forms.ModelForm):
    # Extra confirmation field
    confirm_email = forms.EmailField(
        label=_("Confirm Email"),
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Re-enter email')})
    )

    class Meta:
        model = Student
        # Exclude institution, so it won't appear in the form
        exclude = ['admission_number', 'institution']
        fields = [
            'first_name', 'last_name',
            'email', 'confirm_email',
            'mobile', 'roll_number',
            'enrollment_date', 'admission_type',
            'date_of_birth', 'gender', 'blood_group',
            'status', 'academic_year', 'current_class', 'section',
            'category', 'religion'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'roll_number': forms.TextInput(attrs={'class': 'form-control'}),
            'enrollment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'admission_type': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'blood_group': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'current_class': forms.Select(attrs={'class': 'form-select', 'onchange': 'filterSections()'}),
            'section': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'religion': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # Capture logged-in user
        super().__init__(*args, **kwargs)

        # Auto-set institution from logged-in user
        if self.user and hasattr(self.user, 'profile'):
            self.instance.institution = getattr(self.user.profile, 'institution', None)

        # Default enrollment date
        self.fields['enrollment_date'].initial = timezone.now().date()
        self.fields['roll_number'].required = False
        self.fields['blood_group'].required = False

        # Academic year filtering
        current_date = timezone.now().date()
        academic_years = AcademicYear.objects.filter(
            Q(end_date__gte=current_date) | Q(is_current=True)
        ).order_by('-start_date')
        self.fields['academic_year'].queryset = academic_years
        if not self.instance.pk and not self.initial.get('academic_year'):
            current_academic_year = AcademicYear.objects.filter(is_current=True).first()
            if current_academic_year:
                self.fields['academic_year'].initial = current_academic_year

        # Section filtering based on class
        class_id = self.data.get('current_class') or (self.instance.current_class.pk if self.instance.pk and self.instance.current_class else None)
        if class_id:
            self.fields['section'].queryset = Section.objects.filter(class_name_id=class_id)
        else:
            self.fields['section'].queryset = Section.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        confirm_email = cleaned_data.get('confirm_email')
        enrollment_date = cleaned_data.get('enrollment_date')
        date_of_birth = cleaned_data.get('date_of_birth')
        academic_year = cleaned_data.get('academic_year')
        current_class = cleaned_data.get('current_class')
        section = cleaned_data.get('section')

        # Email match check
        if email and confirm_email and email != confirm_email:
            self.add_error('confirm_email', _('Email addresses do not match'))

        # Enrollment date check
        if enrollment_date and enrollment_date > timezone.now().date():
            self.add_error('enrollment_date', _('Enrollment date cannot be in the future'))

        # Date of birth checks
        if date_of_birth:
            if date_of_birth >= timezone.now().date():
                self.add_error('date_of_birth', _('Date of birth must be in the past'))
            age = timezone.now().date().year - date_of_birth.year
            if age < 3:
                self.add_error('date_of_birth', _('Student must be at least 3 years old'))

        # Enrollment within academic year
        if enrollment_date and academic_year:
            if enrollment_date < academic_year.start_date:
                self.add_error(
                    'enrollment_date',
                    _('Enrollment date cannot be before the academic year start date ({})').format(
                        academic_year.start_date
                    )
                )
            if enrollment_date > academic_year.end_date:
                self.add_error(
                    'enrollment_date',
                    _('Enrollment date cannot be after the academic year end date ({})').format(
                        academic_year.end_date
                    )
                )

        # Section-class consistency
        if section and current_class and section.class_name != current_class:
            self.add_error('section', _('Selected section does not belong to the selected class'))

        return cleaned_data

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if mobile:
            mobile = ''.join(c for c in mobile if c.isdigit() or (c == '+' and mobile.index(c) == 0))
            try:
                phone_regex(mobile)
            except ValidationError:
                raise ValidationError(phone_regex.message)
        return mobile


# -------------------- Guardian Form --------------------
class GuardianForm(BaseForm):
    # Additional phone field for validation
    confirm_phone = forms.CharField(
        required=False,
        validators=[phone_regex],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Confirm Phone Number')}),
        label=_("Confirm Phone")
    )
    
    class Meta:
        model = Guardian
        fields = [
            'student', 'relation', 'name', 'occupation', 'phone', 'confirm_phone',
            'email', 'is_primary', 'address', 'city', 'state', 'pincode'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make some fields not required
        self.fields['phone'].required = False
        self.fields['email'].required = False
        self.fields['address'].required = False
        self.fields['city'].required = False
        self.fields['state'].required = False
        self.fields['pincode'].required = False
        self.fields['confirm_phone'].required = False

    def clean(self):
        cleaned_data = super().clean()
        phone = cleaned_data.get('phone')
        confirm_phone = cleaned_data.get('confirm_phone')
        
        # Check if phone numbers match
        if phone and confirm_phone and phone != confirm_phone:
            self.add_error('confirm_phone', _('Phone numbers do not match'))
            
        # Ensure only one primary guardian per student
        is_primary = cleaned_data.get('is_primary')
        student = cleaned_data.get('student')
        
        if is_primary and student:
            existing_primary = Guardian.objects.filter(
                student=student, 
                is_primary=True
            ).exclude(id=self.instance.id if self.instance else None)
            
            if existing_primary.exists():
                self.add_error('is_primary', _('This student already has a primary guardian'))
                
        return cleaned_data

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove any non-digit characters except leading +
            phone = ''.join(c for c in phone if c.isdigit() or (c == '+' and phone.index(c) == 0))
            
            # Validate using the regex validator
            try:
                phone_regex(phone)
            except ValidationError:
                raise ValidationError(phone_regex.message)
                
        return phone


# -------------------- Medical Information Form --------------------
class StudentMedicalInfoForm(BaseForm):
    class Meta:
        model = StudentMedicalInfo
        fields = [
            'student', 'conditions', 'allergies', 'disability', 
            'disability_type', 'disability_percentage', 
            'emergency_contact_name', 'emergency_contact_phone', 
            'emergency_contact_relation'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make some fields not required
        self.fields['conditions'].required = False
        self.fields['allergies'].required = False
        self.fields['disability_type'].required = False
        self.fields['disability_percentage'].required = False
        self.fields['emergency_contact_name'].required = False
        self.fields['emergency_contact_phone'].required = False
        self.fields['emergency_contact_relation'].required = False

    def clean(self):
        cleaned_data = super().clean()
        disability = cleaned_data.get('disability')
        disability_type = cleaned_data.get('disability_type')
        disability_percentage = cleaned_data.get('disability_percentage')
        
        if disability and not disability_type:
            self.add_error('disability_type', _('Disability type is required when disability is marked'))
            
        if disability_percentage and not disability:
            self.add_error('disability', _('Disability must be checked if disability percentage is provided'))
            
        return cleaned_data

    def clean_emergency_contact_phone(self):
        phone = self.cleaned_data.get('emergency_contact_phone')
        if phone:
            # Remove any non-digit characters except leading +
            phone = ''.join(c for c in phone if c.isdigit() or (c == '+' and phone.index(c) == 0))
            
            # Validate using the regex validator
            try:
                phone_regex(phone)
            except ValidationError:
                raise ValidationError(phone_regex.message)
                
        return phone


# -------------------- Address Form --------------------
class StudentAddressForm(BaseForm):
    class Meta:
        model = StudentAddress
        fields = [
            'student', 'address_type', 'address_line1', 'address_line2',
            'city', 'state', 'pincode', 'country', 'is_current'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default country
        self.fields['country'].initial = 'India'
        # Make some fields not required
        self.fields['address_line2'].required = False


# -------------------- Document Form --------------------

class StudentDocumentForm(BaseForm):
    class Meta:
        model = StudentDocument
        # Keep student in the form so we can assign initial value, but hide it from the user
        fields = ['student', 'doc_type', 'file', 'description', 'is_verified']
        widgets = {
            'student': forms.HiddenInput(),  # hides the field in the form
        }
        
    def __init__(self, *args, **kwargs):
        student = kwargs.pop('student', None)  # optionally pass student from view
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        
        # Automatically assign initial value if student is provided
        if student:
            self.fields['student'].initial = student

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Limit file size to 5MB
            if file.size > 5 * 1024 * 1024:
                raise ValidationError(_('File size must be less than 5MB'))
                
            # Check file extension
            allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx']
            extension = file.name.split('.')[-1].lower()
            if extension not in allowed_extensions:
                raise ValidationError(_('File type not supported. Please upload PDF, JPG, PNG, or DOC files.'))
                
        return file



# -------------------- Transport Form --------------------
class StudentTransportForm(BaseForm):
    class Meta:
        model = StudentTransport
        fields = ['student', 'route', 'pickup_point', 'drop_point', 'transport_fee', 'is_active']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make some fields not required
        self.fields['pickup_point'].required = False
        self.fields['drop_point'].required = False
        self.fields['transport_fee'].required = False


# -------------------- Hostel Form --------------------
class StudentHostelForm(BaseForm):
    class Meta:
        model = StudentHostel
        fields = ['student', 'hostel', 'room_number', 'check_in_date', 'check_out_date', 'hostel_fee']
        widgets = {
            'check_in_date': forms.DateInput(attrs={'type': 'date'}),
            'check_out_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make some fields not required
        self.fields['room_number'].required = False
        self.fields['check_in_date'].required = False
        self.fields['check_out_date'].required = False
        self.fields['hostel_fee'].required = False

    def clean(self):
        cleaned_data = super().clean()
        check_out_date = cleaned_data.get('check_out_date')
        check_in_date = cleaned_data.get('check_in_date')
        
        if check_out_date and check_in_date and check_out_date <= check_in_date:
            self.add_error('check_out_date', _('Check-out date must be after check-in date'))
            
        return cleaned_data


# -------------------- Academic History Form --------------------
class StudentHistoryForm(BaseForm):
    class Meta:
        model = StudentHistory
        fields = [
            'student', 'academic_year', 'class_name', 'section', 'roll_number',
            'final_grade', 'percentage', 'result', 'remarks', 'promoted',
            'previous_school', 'previous_class', 'previous_marks', 'transfer_reason'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make some fields not required
        self.fields['final_grade'].required = False
        self.fields['percentage'].required = False
        self.fields['remarks'].required = False
        self.fields['previous_school'].required = False
        self.fields['previous_class'].required = False
        self.fields['previous_marks'].required = False
        self.fields['transfer_reason'].required = False

    def clean(self):
        cleaned_data = super().clean()
        percentage = cleaned_data.get('percentage')
        result = cleaned_data.get('result')
        
        if percentage is not None:
            if result == "PASS" and percentage < 33:
                self.add_error('percentage', _('Percentage should be at least 33 for PASS result'))
            elif result == "FAIL" and percentage >= 33:
                self.add_error('result', _('Result should be PASS if percentage is 33 or above'))
                
        # Check for unique roll number within the same class and academic year
        academic_year = cleaned_data.get('academic_year')
        class_name = cleaned_data.get('class_name')
        section = cleaned_data.get('section')
        roll_number = cleaned_data.get('roll_number')
        
        if academic_year and class_name and section and roll_number:
            existing = StudentHistory.objects.filter(
                academic_year=academic_year,
                class_name=class_name,
                section=section,
                roll_number=roll_number
            ).exclude(id=self.instance.id if self.instance else None)
            
            if existing.exists():
                self.add_error('roll_number', _('Roll number must be unique within the same class and academic year'))
                
        return cleaned_data


# -------------------- Search Forms --------------------

class StudentSearchForm(BaseSearchForm):
    admission_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Admission Number')})
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('First Name')})
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Last Name')})
    )
    class_name = forms.ModelChoiceField(
        required=False,
        queryset=None,  # Will be set in __init__
        empty_label=_("All Classes")
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', _('All Statuses'))] + list(Student.STATUS_CHOICES),
    )
    
    def __init__(self, *args, **kwargs):
        from apps.academics.models import Class  # Import here to avoid circular imports
        super().__init__(*args, **kwargs)
        self.fields['class_name'].queryset = Class.objects.all()


class GuardianSearchForm(BaseSearchForm):
    name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Guardian Name')})
    )
    student_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Student Name')})
    )
    relation = forms.ChoiceField(
        required=False,
        choices=[('', _('All Relations'))] + list(Guardian.RELATION_CHOICES),
    )


# -------------------- Bulk Upload Form --------------------
class StudentBulkUploadForm(BaseSearchForm):
    file = forms.FileField(
        label=_('CSV File'),
        help_text=_('Upload a CSV file containing student data.'),
        widget=forms.FileInput(attrs={'accept': '.csv'})
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file extension
            if not file.name.endswith('.csv'):
                raise ValidationError(_('File must be a CSV file.'))
                
            # Check file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                raise ValidationError(_('File size must be less than 5MB.'))
                
        return file


# -------------------- Quick Action Forms --------------------
class StudentStatusForm(BaseForm):
    class Meta:
        model = Student
        fields = ['status']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active/inactive statuses for quick changes
        self.fields['status'].choices = [
            ('ACTIVE', _('Active')),
            ('INACTIVE', _('Inactive')),
        ]


class StudentClassForm(BaseForm):
    class Meta:
        model = Student
        fields = ['current_class', 'section']
        
    def clean(self):
        cleaned_data = super().clean()
        # Check if section belongs to the selected class
        current_class = cleaned_data.get('current_class')
        section = cleaned_data.get('section')
        if section and current_class and section.class_obj != current_class:
            self.add_error('section', _('Selected section does not belong to the selected class'))
        return cleaned_data
    
 

class StudentFilterForm(BaseSearchForm):

   
    admission_number = forms.CharField(
        required=False,
        label="Admission Number",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter admission number"})
    )
    first_name = forms.CharField(
        required=False,
        label="First Name",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter first name"})
    )
    last_name = forms.CharField(
        required=False,
        label="Last Name",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter last name"})
    )
    student_class = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        required=False,
        label="Class",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.all(),
        required=False,
        label="Section",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        required=False,
        label="Academic Year",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    STATUS_CHOICES = [
        ('', '---------'),
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('ALUMNI', 'Alumni'),
        ('SUSPENDED', 'Suspended'),
        ('WITHDRAWN', 'Withdrawn'),
    ]
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label="Status",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    gender = forms.ChoiceField(
        choices=[('', 'All Genders')] + list(Student.GENDER_CHOICES),
        required=False,
        label='Gender'
    )
    has_hostel = forms.ChoiceField(
        choices=[('', 'All Students'), ('yes', 'Yes'), ('no', 'No')],
        required=False,
        label='Hostel Student'
    )
    has_disability = forms.ChoiceField(
        choices=[('', 'All Students'), ('yes', 'Yes'), ('no', 'No')],
        required=False,
        label='Has Disability'
    )
    category = forms.ChoiceField(
        choices=[('', 'All Category')] + list(Student.CATEGORY_CHOICES),
        required=False,
        label='category'
    )
    religion = forms.ChoiceField(
        choices=[('', 'All Religions')] + list(Student.RELIGION_CHOICES),
        required=False,
        label='Religion'
    )
    has_transport = forms.ChoiceField(
        choices=[('', 'All Students'), ('yes', 'Yes'), ('no', 'No')],
        required=False,
        label='Uses Transport'
    )
  

class StudentIdentificationForm(forms.ModelForm):
    class Meta:
        model = StudentIdentification
        fields = '__all__'
        exclude = ['student']  # Exclude student field if it's set elsewhere
        widgets = {
            'aadhaar_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '123456789012',
                'data-mask': '0000 0000 0000',
            }),
            'abc_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter ABC ID')
            }),
            'shiksha_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter Shiksha ID')
            }),
            'pan_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ABCDE1234F',
                'style': 'text-transform: uppercase;'
            }),
            'passport_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter Passport Number'),
                'style': 'text-transform: uppercase;'
            }),
        }
        labels = {
            'aadhaar_number': _("Aadhaar Number"),
            'abc_id': _("ABC ID"),
            'shiksha_id': _("Shiksha ID"),
            'pan_number': _("PAN Number"),
            'passport_number': _("Passport Number"),
        }
        help_texts = {
            'aadhaar_number': _("12-digit number without spaces"),
            'pan_number': _("Format: ABCDE1234F"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set all fields as not required
        for field in self.fields:
            self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()
        # Add any cross-field validation here
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Custom save logic if needed
        if commit:
            instance.save()
        return instance