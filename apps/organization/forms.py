
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (Institution, Department, Branch, InstitutionCompliance, Affiliation, 
                     Accreditation, Partnership)
from apps.core.utils import get_user_institution

class PartnershipForm(forms.ModelForm):
    class Meta:
        model = Partnership
        fields = [
            'partner_name', 'partner_type', 'description', 
            'start_date', 'end_date', 'document',
            'contact_person', 'contact_email', 'contact_phone',
            'is_active', 'renewal_required'
        ]
        widgets = {
            'partner_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter partner organization name'
            }),
            'partner_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the partnership objectives and scope'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }),
            'document': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contact person name'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contact@example.com'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91 9876543210'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'renewal_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError(
                "Start date cannot be after End date."
            )
        return cleaned_data
    

class AccreditationForm(forms.ModelForm):
    class Meta:
        model = Accreditation
        fields = [
            'name', 'grade_or_level', 'awarded_by',
            'valid_from', 'valid_to', 'certificate',
            'is_active', 'renewal_required'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., NAAC, ISO 9001, NBA'
            }),
            'grade_or_level': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., A++, ISO 9001:2015'
            }),
            'awarded_by': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Awarding authority'
            }),
            'valid_from': forms.DateInput(attrs={
                'type': 'date', 'class': 'form-control'
            }),
            'valid_to': forms.DateInput(attrs={
                'type': 'date', 'class': 'form-control'
            }),
            'certificate': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'renewal_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Auto-assign institution if creating new record
        if self.request and not self.instance.pk:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                self.instance.institution = user_institution

        # Add Bootstrap classes for checkboxes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get("valid_from")
        valid_to = cleaned_data.get("valid_to")

        if valid_from and valid_to and valid_from > valid_to:
            raise forms.ValidationError("Valid From date cannot be after Valid To date.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Auto-assign institution again just in case
        if self.request and not instance.institution_id:
            instance.institution = get_user_institution(self.request.user)
        if commit:
            instance.save()
        return instance

class AffiliationForm(forms.ModelForm):
    class Meta:
        model = Affiliation
        fields = [
            'name', 
            'code', 
            'valid_from', 
            'valid_to', 
            'document', 
            'is_active', 
            'renewal_required', 
            'renewal_notice_period'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter affiliation name (e.g., CBSE, UGC, AICTE)'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter affiliation code (optional)'
            }),
            'valid_from': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'valid_to': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'document': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'renewal_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'renewal_notice_period': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1'
            }),
        }
        help_texts = {
            'renewal_notice_period': 'Days before expiry to send renewal notice',
            'valid_from': 'Date when this affiliation becomes effective',
            'valid_to': 'Date when this affiliation expires',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Make fields optional as per model
        self.fields['code'].required = False
        self.fields['valid_from'].required = False
        self.fields['valid_to'].required = False
        self.fields['document'].required = False

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')

        # Validate date range
        if valid_from and valid_to:
            if valid_from > valid_to:
                raise forms.ValidationError({
                    'valid_to': 'Valid To date cannot be earlier than Valid From date.'
                })

        # Validate renewal notice period
        renewal_notice_period = cleaned_data.get('renewal_notice_period')
        if renewal_notice_period and renewal_notice_period < 0:
            raise forms.ValidationError({
                'renewal_notice_period': 'Renewal notice period cannot be negative.'
            })

        return cleaned_data

    def clean_document(self):
        document = self.cleaned_data.get('document')
        if document:
            # Validate file size (5MB limit)
            if document.size > 5 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 5MB.")
            
            # Validate file extension
            valid_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            if not any(document.name.lower().endswith(ext) for ext in valid_extensions):
                raise forms.ValidationError(
                    "Unsupported file format. Please upload PDF, Word, or image files."
                )
        
        return document

class ColorSettingsForm(forms.ModelForm):
    class Meta:
        model = Institution
        fields = '__all__'
        widgets = {
            'primary_color': forms.TextInput(attrs={'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color'}),
            'accent_color': forms.TextInput(attrs={'type': 'color'}),
            'text_dark_color': forms.TextInput(attrs={'type': 'color'}),
            'text_light_color': forms.TextInput(attrs={'type': 'color'}),
            'text_muted_color': forms.TextInput(attrs={'type': 'color'}),
        }

class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution
        fields = [
            'name', 'short_name', 'slug', 'code', 'type', 'address', 'city', 'state', 
            'country', 'pincode', 'website', 'contact_email', 'contact_phone', 
            'alternate_phone', 'logo', 'stamp', 'favicon', 'banner', 'primary_color',
            'secondary_color', 'accent_color', 'text_dark_color', 'text_light_color',
            'text_muted_color', 'academic_year_start', 'academic_year_end', 'timezone',
            'fiscal_year_start', 'language', 'currency', 'is_active', 'established_date'
        ]
        widgets = {
            'academic_year_start': forms.DateInput(attrs={'type': 'date'}),
            'academic_year_end': forms.DateInput(attrs={'type': 'date'}),
            'fiscal_year_start': forms.DateInput(attrs={'type': 'date'}),
            'established_date': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'slug': 'A short, unique identifier for URLs (letters, numbers, hyphens, underscores)',
            'code': 'Unique institutional code (max 20 characters)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field not in ['logo', 'stamp', 'favicon', 'banner', 'is_active']:
                self.fields[field].widget.attrs.update({'class': 'form-control'})
            elif field in ['logo', 'stamp', 'favicon', 'banner']:
                self.fields[field].widget.attrs.update({'class': 'form-control'})


class DepartmentForm(forms.ModelForm):
    # Add institution as a select field if user has multiple institutions access
    institution = forms.ModelChoiceField(
        queryset=Institution.objects.none(),
        required=True,
        empty_label="Select Institution"
    )
    
    class Meta:
        model = Department
        fields = [
            'institution', 'name', 'code', 'short_name', 'department_type', 
            'description', 'head_of_department', 'email', 'phone', 'office_location',
            'is_active', 'established_date'
        ]
        widgets = {
            'established_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Set institution queryset based on user permissions
        if self.request and self.request.user.is_authenticated:
            if self.request.user.is_superuser:
                # Superusers can select any institution
                self.fields['institution'].queryset = Institution.objects.all()
            elif hasattr(self.request.user, 'institution') and self.request.user.institution:
                # Regular users can only use their institution
                self.fields['institution'].queryset = Institution.objects.filter(id=self.request.user.institution.id)
                # Set initial value to user's institution
                self.fields['institution'].initial = self.request.user.institution
            else:
                # Users without institution can't create departments
                self.fields['institution'].queryset = Institution.objects.none()
        
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Make required fields more explicit
        self.fields['name'].widget.attrs['placeholder'] = 'Enter department name'
        self.fields['code'].widget.attrs['placeholder'] = 'Enter department code'
    
    def clean(self):
        cleaned_data = super().clean()
        institution = cleaned_data.get('institution')
        
        # Validate that institution is set
        if not institution:
            if self.request and hasattr(self.request.user, 'institution') and self.request.user.institution:
                # Auto-set from user if available
                cleaned_data['institution'] = self.request.user.institution
            else:
                raise forms.ValidationError("Institution is required for department creation.")
        
        # Validate unique code within institution
        code = cleaned_data.get('code')
        if institution and code:
            existing_dept = Department.objects.filter(
                institution=institution, 
                code=code
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_dept.exists():
                raise forms.ValidationError(
                    f"A department with code '{code}' already exists in {institution.name}."
                )
        
        return cleaned_data

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = [
            'institution', 'name', 'code', 'is_main_campus', 'address', 'city', 
            'state', 'country', 'pincode', 'contact_email', 'contact_phone', 
            'website', 'branch_manager', 'is_active', 'established_date'
        ]
        widgets = {
            'established_date': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.request and hasattr(self.request.user, 'institution'):
            self.fields['institution'].initial = self.request.user.institution
            self.fields['institution'].widget.attrs['readonly'] = True
        
        for field in self.fields:
            if field != 'is_main_campus':
                self.fields[field].widget.attrs.update({'class': 'form-control'})


class InstitutionComplianceForm(forms.ModelForm):
    class Meta:
        model = InstitutionCompliance
    
        fields = [
            'institution',
            'gst_number', 'pan_number', 'tan_number',
            'registration_no', 'registration_authority', 'registration_date',
            'pf_registration_no', 'esi_registration_no',
            'udise_code', 'aicte_code', 'ugc_code', 'is_active'
        ]
        widgets = {
            'registration_date': forms.DateInput(attrs={'type': 'date'}),
            'gst_number': forms.TextInput(attrs={'placeholder': 'e.g., 07AABCU9603R1ZM'}),
            'pan_number': forms.TextInput(attrs={'placeholder': 'e.g., AABCU9603R'}),
            'tan_number': forms.TextInput(attrs={'placeholder': 'e.g., BLRE12345F'}),
            'udise_code': forms.TextInput(attrs={'placeholder': '11-digit UDISE code'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        gst_number = cleaned_data.get('gst_number')
        pan_number = cleaned_data.get('pan_number')

        if gst_number and len(gst_number) != 15:
            self.add_error('gst_number', "GST number must be 15 characters long.")
        if pan_number and len(pan_number) != 10:
            self.add_error('pan_number', "PAN number must be 10 characters long.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Auto-set institution from logged-in user
        if self.request and hasattr(self.request.user, 'institution'):
            instance.institution = self.request.user.institution
        if commit:
            instance.save()
        return instance


class AffiliationForm(forms.ModelForm):
    class Meta:
        model = Affiliation
        fields = [
            'name', 'code', 'valid_from', 'valid_to', 'document',
            'is_active', 'renewal_required', 'renewal_notice_period'
        ]
        widgets = {
            'valid_from': forms.DateInput(attrs={'type': 'date'}),
            'valid_to': forms.DateInput(attrs={'type': 'date'}),
            'renewal_notice_period': forms.NumberInput(attrs={'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Apply Bootstrap form-control or form-check-input styling
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class': 'form-control-file'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

        # Add placeholders for clarity
        self.fields['name'].widget.attrs['placeholder'] = "Enter affiliation name"
        self.fields['code'].widget.attrs['placeholder'] = "Enter code"
        self.fields['renewal_notice_period'].widget.attrs['placeholder'] = "e.g., 30 (days)"

        # Set institution automatically when creating new record
        if self.request and not self.instance.pk:
            user_institution = get_user_institution(self.request.user)
            if user_institution:
                self.instance.institution = user_institution

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')

        if valid_from and valid_to and valid_from > valid_to:
            raise forms.ValidationError("Valid From date cannot be after Valid To date.")

        return cleaned_data




class InstitutionFilterForm(forms.Form):
    type = forms.ChoiceField(
        choices=[('', 'All Types')] + Institution._meta.get_field('type').choices,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    country = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter by country'})
    )
    is_active = forms.ChoiceField(
        choices=[('', 'All Status'), ('true', 'Active'), ('false', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by name or code'})
    )