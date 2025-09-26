from django import forms
from .models import (Vehicle, MaintenanceRecord,TransportAttendance,TransportAssignment,StudentTransport
,StudentTransport, TransportAssignment, RouteStop,Driver,Route)
from apps.students.models import Student
from apps.core.utils import get_user_institution
from django import forms
from datetime import datetime, timedelta

class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = [
            'user', 'license_number', 'license_type', 'license_expiry',
            'experience', 'address', 'emergency_contact',
            'photo', 'id_proof', 'license_photo', 'is_active'
        ]
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter license number'}),
            'license_type': forms.Select(attrs={'class': 'form-select'}),
            'license_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'experience': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'Years of experience'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Driver address'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency contact number'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'}),
            'id_proof': forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'}),
            'license_photo': forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    # Optional: Add Bootstrap classes to labels automatically
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.ClearableFileInput, forms.Select, forms.DateInput)):
                field.widget.attrs['class'] = 'form-control'
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            if isinstance(field.widget, forms.ClearableFileInput):
                field.widget.attrs['class'] = 'form-control form-control-sm'

                
class DriverFilterForm(forms.Form):
    STATUS_CHOICES = (
        ("", "All"),
        ("active", "Active"),
        ("inactive", "Inactive"),
    )
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    search = forms.CharField(max_length=100, required=False)

class RouteForm(forms.ModelForm):
    estimated_time = forms.DurationField(
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'HH:MM:SS',
            }
        ),
        label='Estimated Time (HH:MM:SS)',
        help_text='Enter estimated time in HH:MM:SS format'
    )

    class Meta:
        model = Route
        fields = ['name', 'start_point', 'end_point', 'distance', 'estimated_time', 'fare', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter route name'}),
            'start_point': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter starting point'}),
            'end_point': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter ending point'}),
            'distance': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Distance in km'}),
            'fare': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter fare amount'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'distance': 'Distance (km)',
            'fare': 'Fare (₹)',
        }

    def clean_estimated_time(self):
        val = self.cleaned_data.get('estimated_time')
        if isinstance(val, str):
            try:
                hours, minutes, seconds = map(int, val.split(':'))
                return timedelta(hours=hours, minutes=minutes, seconds=seconds)
            except:
                raise forms.ValidationError("Enter time in HH:MM:SS format")
        return val



class RouteFilterForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Search routes...'
    }))
    status = forms.ChoiceField(required=False, choices=[
        ('', 'All Status'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], widget=forms.Select(attrs={'class': 'form-select'}))

class RouteStopFilterForm(forms.Form):
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    route = forms.ModelChoiceField(
        queryset=None, 
        empty_label="All Routes", 
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.request:
            institution = get_user_institution(self.request.user)
            self.fields['route'].queryset = Route.objects.filter(
                institution=institution, 
                is_active=True
            )

class RouteStopForm(forms.ModelForm):
    class Meta:
        model = RouteStop
        fields = ['route', 'name', 'address', 'sequence', 'pickup_time', 'drop_time']
        widgets = {
            'route': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Stop Name'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Address'}),
            'sequence': forms.NumberInput(attrs={'class': 'form-control'}),
            'pickup_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'drop_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }


class TransportAssignmentForm(forms.ModelForm):
    class Meta:
        model = TransportAssignment
        fields = ['vehicle', 'driver', 'route', 'start_date', 'end_date', 'is_active']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Filter querysets based on user's institution
        if self.request and hasattr(self.request.user, 'institution'):
            institution = self.request.user.institution
            self.fields['vehicle'].queryset = Vehicle.objects.filter(institution=institution, is_active=True)
            self.fields['driver'].queryset = Driver.objects.filter(institution=institution, is_active=True)
            self.fields['route'].queryset = Route.objects.filter(institution=institution, is_active=True)

class TransportAssignmentFilterForm(forms.Form):
    STATUS_CHOICES = (
        ('', 'All Status'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
        ('scheduled', 'Scheduled'),
    )
    
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.none(),
        required=False,
        empty_label="All Vehicles",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    driver = forms.ModelChoiceField(
        queryset=Driver.objects.none(),
        required=False,
        empty_label="All Drivers",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    route = forms.ModelChoiceField(
        queryset=Route.objects.none(),
        required=False,
        empty_label="All Routes",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.request and hasattr(self.request.user, 'institution'):
            institution = self.request.user.institution
            self.fields['vehicle'].queryset = Vehicle.objects.filter(institution=institution)
            self.fields['driver'].queryset = Driver.objects.filter(institution=institution)
            self.fields['route'].queryset = Route.objects.filter(institution=institution)


class StudentTransportForm(forms.ModelForm):
    class Meta:
        model = StudentTransport
        fields = [
            'student',
            'transport_assignment',
            'pickup_stop',
            'drop_stop',
            'start_date',
            'end_date',
            'is_active',
        ]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'transport_assignment': forms.Select(attrs={'class': 'form-select'}),
            'pickup_stop': forms.Select(attrs={'class': 'form-select'}),
            'drop_stop': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class StudentTransportFilterForm(forms.Form):
    STATUS_CHOICES = (
        ("", "All"),
        ("active", "Active"),
        ("inactive", "Inactive"),
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES, required=False, label="Status"
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)  
        super().__init__(*args, **kwargs)


class TransportAttendanceForm(forms.ModelForm):
    class Meta:
        model = TransportAttendance
        fields = ['student_transport', 'date', 'pickup_status', 'drop_status', 'pickup_time', 'drop_time', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'pickup_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'drop_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            institution = getattr(user, 'institution', None)
            self.fields['student_transport'].queryset = StudentTransport.objects.filter(institution=institution)
        self.fields['student_transport'].widget.attrs.update({'class': 'form-select'})
        self.fields['pickup_status'].widget.attrs.update({'class': 'form-select'})
        self.fields['drop_status'].widget.attrs.update({'class': 'form-select'})

class MaintenanceRecordForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRecord
        fields = [
            'maintenance_type',
            'date',
            'odometer_reading',
            'description',
            'cost',
            'garage',
            'next_due_date',
            'next_due_reading',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'next_due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'maintenance_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'garage': forms.TextInput(attrs={'class': 'form-control'}),
            'odometer_reading': forms.NumberInput(attrs={'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control'}),
            'next_due_reading': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            'vehicle_number', 'vehicle_type', 'make', 'model', 'year', 
            'color', 'capacity', 'fuel_type', 'insurance_number', 
            'insurance_expiry', 'registration_date', 'registration_expiry', 'is_active'
        ]
        widgets = {
            'insurance_expiry': forms.DateInput(attrs={'type': 'date'}),
            'registration_date': forms.DateInput(attrs={'type': 'date'}),
            'registration_expiry': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

class VehicleFilterForm(forms.Form):
    vehicle_type = forms.ChoiceField(
        choices=[('', 'All')] + list(Vehicle.VEHICLE_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    fuel_type = forms.ChoiceField(
        choices=[('', 'All')] + list(Vehicle.FUEL_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All'), ('active', 'Active'), ('inactive', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)