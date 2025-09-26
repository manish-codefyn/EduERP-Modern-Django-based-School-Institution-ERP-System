from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import F
from .models import (
    Hostel, HostelFacility, Room, RoomAmenity, HostelAllocation, 
    HostelFeeStructure, HostelAttendance, HostelVisitorLog, 
    HostelInventory, MaintenanceRequest
)
from apps.core.utils import get_user_institution
from apps.students.models import Student


class HostelForm(forms.ModelForm):
    class Meta:
        model = Hostel
        fields = [
            'name', 'code', 'gender_type', 'capacity', 'warden', 
            'assistant_warden', 'contact_number', 'email', 'address', 
            'facilities', 'monthly_charges', 'security_deposit', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter hostel name')
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter hostel code')
            }),
            'gender_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'warden': forms.Select(attrs={
                'class': 'form-select'
            }),
            'assistant_warden': forms.Select(attrs={
                'class': 'form-select'
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter contact number')
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter email address')
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('Enter hostel address'),
                'rows': 3
            }),
            'facilities': forms.SelectMultiple(attrs={
                'class': 'form-select'
            }),
            'monthly_charges': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': 0
            }),
            'security_deposit': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': 0
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'code': _('Hostel Code'),
            'gender_type': _('Gender Type'),
            'warden': _('Warden'),
            'assistant_warden': _('Assistant Warden'),
            'facilities': _('Facilities'),
            'monthly_charges': _('Monthly Charges (₹)'),
            'security_deposit': _('Security Deposit (₹)'),
            'is_active': _('Is Active'),
        }

    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        # Filter staff to only those from the same institution
        if self.institution:
            self.fields['warden'].queryset = self.fields['warden'].queryset.filter(
                institution=self.institution
            )
            self.fields['assistant_warden'].queryset = self.fields['assistant_warden'].queryset.filter(
                institution=self.institution
            )

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            # Check if code is unique for the institution
            qs = Hostel.objects.filter(code=code)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise ValidationError(_('A hostel with this code already exists.'))
        return code

    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')
        if capacity <= 0:
            raise ValidationError(_('Capacity must be greater than zero.'))
        return capacity


class HostelFacilityForm(forms.ModelForm):
    class Meta:
        model = HostelFacility
        fields = ['name', 'description', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter facility name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter facility description (optional)'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., wifi, tv, snow'
            }),
        }
        labels = {
            'name': 'Facility Name',
            'description': 'Description',
            'icon': 'Icon Class',
        }
        help_texts = {
            'icon': 'Enter Bootstrap Icons class name (without the "bi-" prefix)',
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name and len(name) < 2:
            raise forms.ValidationError("Facility name must be at least 2 characters long.")
        return name

    def clean_icon(self):
        icon = self.cleaned_data.get('icon')
        if icon and len(icon) > 50:
            raise forms.ValidationError("Icon class name must be 50 characters or less.")
        return icon

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = [
            'hostel', 'room_number', 'floor', 'room_type', 'capacity', 
            'amenities', 'is_available', 'maintenance_required', 'maintenance_notes'
        ]
        widgets = {
            'hostel': forms.Select(attrs={
                'class': 'form-select'
            }),
            'room_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter room number')
            }),
            'floor': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'room_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'amenities': forms.SelectMultiple(attrs={
                'class': 'form-select'
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'maintenance_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'maintenance_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('Enter maintenance notes'),
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        # Filter hostels to only those from the same institution
        if self.institution:
            self.fields['hostel'].queryset = self.fields['hostel'].queryset.filter(
                institution=self.institution
            )

    def clean_room_number(self):
        room_number = self.cleaned_data.get('room_number')
        hostel = self.cleaned_data.get('hostel')
        
        if hostel and room_number:
            # Check if room number is unique for the hostel
            qs = Room.objects.filter(hostel=hostel, room_number=room_number)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise ValidationError(_('A room with this number already exists in this hostel.'))
        
        return room_number

    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')
        if capacity <= 0:
            raise ValidationError(_('Capacity must be greater than zero.'))
        return capacity

class RoomAmenityForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
    
    class Meta:
        model = RoomAmenity
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter amenity name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter amenity description (optional)'
            }),
        }
        labels = {
            'name': 'Amenity Name',
            'description': 'Description',
        }
        help_texts = {
            'name': 'Enter the name of the room amenity (e.g., Air Conditioner, Study Table)',
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name and len(name) < 2:
            raise forms.ValidationError("Amenity name must be at least 2 characters long.")
        
        # Check for duplicate name within the same institution
        if self.request and name:
            institution = get_user_institution(self.request.user)
            queryset = RoomAmenity.objects.filter(name__iexact=name, institution=institution)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(id=self.instance.id)
            if queryset.exists():
                raise forms.ValidationError("An amenity with this name already exists in your institution.")
        
        return name
    
    
class HostelAllocationForm(forms.ModelForm):
    class Meta:
        model = HostelAllocation
        fields = ['student', 'room', 'date_from', 'date_to', 'is_active']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'date_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_to': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        # Filter students to only those from the same institution
        if self.institution:
            self.fields['student'].queryset = self.fields['student'].queryset.filter(
                institution=self.institution
            )
            
            # Get available rooms
            available_rooms = Room.objects.filter(
                hostel__institution=self.institution,
                is_available=True
            ).annotate(
                available_beds=F('capacity') - F('current_occupancy')
            ).filter(available_beds__gt=0)
            
            if available_rooms.exists():
                self.fields['room'].queryset = available_rooms
                self.fields['room'].empty_label = "Select a room"
            else:
                # If no rooms available, show all rooms but disable the field
                self.fields['room'].queryset = Room.objects.filter(
                    hostel__institution=self.institution
                )
                self.fields['room'].widget.attrs['disabled'] = True
                self.fields['room'].help_text = "No rooms with available capacity. Please check room availability first."
                
            # Set initial date to today for new allocations
            if not self.instance.pk:
                self.fields['date_from'].initial = timezone.now().date()
                self.fields['is_active'].initial = True

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        room = cleaned_data.get('room')
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        is_active = cleaned_data.get('is_active')

        # Check if room is disabled (no available capacity)
        if self.fields['room'].widget.attrs.get('disabled'):
            raise ValidationError(_("Cannot create allocation - no rooms with available capacity."))

        # Check student already has an active allocation
        if student and is_active:
            qs = HostelAllocation.objects.filter(student=student, is_active=True)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError({
                    'student': _('This student already has an active hostel allocation.')
                })

        # Check room capacity
        if room and is_active:
            if room.current_occupancy >= room.capacity:
                raise ValidationError({
                    'room': _('This room is already at full capacity.')
                })

        # Validate date range
        if date_from and date_to and date_to < date_from:
            raise ValidationError({
                'date_to': _('End date cannot be before start date.')
            })

        # Check for past start date in active allocations
        if is_active and date_from and date_from < timezone.now().date():
            raise ValidationError({
                'date_from': _('Start date cannot be in the past for active allocations.')
            })

        return cleaned_data


class HostelFeeStructureForm(forms.ModelForm):
    class Meta:
        model = HostelFeeStructure
        fields = [
            'hostel', 'room_type', 'amount', 'frequency', 
            'effective_from', 'effective_to', 'is_active'
        ]
        widgets = {
            'hostel': forms.Select(attrs={
                'class': 'form-select'
            }),
            'room_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': 0
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'effective_from': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'effective_to': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'amount': _('Amount (₹)'),
        }

    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        # Filter hostels to only those from the same institution
        if self.institution:
            self.fields['hostel'].queryset = self.fields['hostel'].queryset.filter(
                institution=self.institution
            )

    def clean(self):
        cleaned_data = super().clean()
        effective_from = cleaned_data.get('effective_from')
        effective_to = cleaned_data.get('effective_to')
        hostel = cleaned_data.get('hostel')
        room_type = cleaned_data.get('room_type')
        is_active = cleaned_data.get('is_active')

        # Validate date range
        if effective_from and effective_to and effective_to < effective_from:
            raise ValidationError({
                'effective_to': _('End date cannot be before start date.')
            })

        # Check for overlapping fee structures
        if hostel and room_type and effective_from and is_active:
            qs = HostelFeeStructure.objects.filter(
                hostel=hostel,
                room_type=room_type,
                is_active=True
            )
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            
            # Check for overlapping date ranges
            overlapping = qs.filter(
                effective_from__lte=effective_to if effective_to else effective_from,
                effective_to__gte=effective_from
            )
            if overlapping.exists():
                raise ValidationError(
                    _('An active fee structure already exists for this hostel and room type during the specified period.')
                )

        return cleaned_data

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise ValidationError(_('Amount must be greater than zero.'))
        return amount


class HostelAttendanceForm(forms.ModelForm):
    class Meta:
        model = HostelAttendance
        fields = ['student', 'date', 'present', 'notes']
        widgets = {
            'student': forms.Select(attrs={
                'class': 'form-select'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'readonly': 'readonly',  # Make date field readonly
            }),
            'present': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('Enter any notes'),
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)

        # Filter students by institution and active hostel allocations
        if self.institution:
            self.fields['student'].queryset = self.fields['student'].queryset.filter(
                institution=self.institution,
                hostel_allocations__is_active=True
            ).distinct()

        # Set the date field to today
        self.fields['date'].initial = timezone.now().date()
        # Optional: make it hidden if you don't even want it displayed
        # self.fields['date'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        date = cleaned_data.get('date')

        # Force date to today (in case someone tries to tamper via POST)
        today = timezone.now().date()
        cleaned_data['date'] = today

        # Check for duplicate attendance records
        if student:
            qs = HostelAttendance.objects.filter(student=student, date=today)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise ValidationError(
                    _('An attendance record already exists for this student today.')
                )

        return cleaned_data

class HostelVisitorLogForm(forms.ModelForm):
    class Meta:
        model = HostelVisitorLog
        fields = ['visitor_name', 'student_visited', 'purpose', 'id_proof', 'id_number', 'entry_time', 'exit_time']
        widgets = {
            'visitor_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter visitor full name'
            }),
            'student_visited': forms.Select(attrs={
                'class': 'form-control select2'
            }),
            'purpose': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter purpose of visit'
            }),
            'id_proof': forms.Select(attrs={
                'class': 'form-control'
            }),
            'id_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter ID number'
            }),
            'entry_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'exit_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }
        labels = {
            'visitor_name': 'Visitor Name',
            'student_visited': 'Student Visited',
            'purpose': 'Purpose of Visit',
            'id_proof': 'ID Proof Type',
            'id_number': 'ID Number',
            'entry_time': 'Entry Time',
            'exit_time': 'Exit Time',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Filter students by institution
        if self.request:
            institution = get_user_institution(self.request.user)
            self.fields['student_visited'].queryset = Student.objects.filter(
                institution=institution,
                status="ACTIVE"
            ).select_related('user')
        else:
            self.fields['student_visited'].queryset = Student.objects.none()
    def clean_visitor_name(self):
        visitor_name = self.cleaned_data.get('visitor_name')
        if visitor_name and len(visitor_name) < 2:
            raise forms.ValidationError("Visitor name must be at least 2 characters long.")
        return visitor_name

    def clean_entry_time(self):
        entry_time = self.cleaned_data.get('entry_time')
        if entry_time and entry_time > timezone.now():
            raise forms.ValidationError("Entry time cannot be in the future.")
        return entry_time

    def clean_exit_time(self):
        exit_time = self.cleaned_data.get('exit_time')
        entry_time = self.cleaned_data.get('entry_time')
        
        if exit_time:
            if exit_time > timezone.now():
                raise forms.ValidationError("Exit time cannot be in the future.")
            if entry_time and exit_time <= entry_time:
                raise forms.ValidationError("Exit time must be after entry time.")
        
        return exit_time

class HostelInventoryForm(forms.ModelForm):
    class Meta:
        model = HostelInventory
        fields = [
            'hostel', 'item_name', 'quantity', 'condition', 
            'last_maintenance', 'next_maintenance', 'notes'
        ]
        widgets = {
            'hostel': forms.Select(attrs={
                'class': 'form-select'
            }),
            'item_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter item name')
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'condition': forms.Select(attrs={
                'class': 'form-select'
            }),
            'last_maintenance': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'next_maintenance': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('Enter any notes'),
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        # Filter hostels to only those from the same institution
        if self.institution:
            self.fields['hostel'].queryset = self.fields['hostel'].queryset.filter(
                institution=self.institution
            )

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity < 0:
            raise ValidationError(_('Quantity cannot be negative.'))
        return quantity

    def clean(self):
        cleaned_data = super().clean()
        last_maintenance = cleaned_data.get('last_maintenance')
        next_maintenance = cleaned_data.get('next_maintenance')

        # Validate maintenance dates
        if last_maintenance and next_maintenance and next_maintenance < last_maintenance:
            raise ValidationError({
                'next_maintenance': _('Next maintenance date cannot be before last maintenance date.')
            })

        return cleaned_data

class MaintenanceRequestForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = [
            'hostel', 'room', 'title', 'description', 
            'priority', 'status', 'assigned_to', 'cost'
        ]
        widgets = {
            'hostel': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter maintenance title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter detailed description', 'rows': 4}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.request and hasattr(self.request.user, 'staff'):
            institution = get_user_institution(self.request.user)
            
            # Filter hostels and rooms by institution
            self.fields['hostel'].queryset = self.fields['hostel'].queryset.filter(
                institution=institution
            )
            self.fields['room'].queryset = self.fields['room'].queryset.filter(
                hostel__institution=institution
            )
            
            # Filter staff by institution for assignment
            self.fields['assigned_to'].queryset = self.fields['assigned_to'].queryset.filter(
                institution=institution
            )
            
            
    def clean_cost(self):
        cost = self.cleaned_data.get('cost')
        if cost is not None and cost < 0:
            raise ValidationError(_('Cost cannot be negative.'))
        return cost

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get('room')
        hostel = cleaned_data.get('hostel')

        # Validate that room belongs to selected hostel
        if room and hostel and room.hostel != hostel:
            raise ValidationError({'room': _('The selected room does not belong to the selected hostel.')})

        return cleaned_data
