import csv
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView,View
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count, Sum, F
from django.utils import timezone

from apps.core.mixins import DirectorRequiredMixin, FinanceAccessRequiredMixin
from apps.core.utils import get_user_institution
from .models import Hostel, Room, HostelAllocation, HostelFeeStructure, HostelFacility, RoomAmenity
from .forms import ( RoomAmenityForm,RoomForm,HostelFacilityForm,HostelForm,HostelAllocationForm,HostelAttendanceForm,HostelFeeStructureForm)


class HostelListView(DirectorRequiredMixin, ListView):
    model = Hostel
    template_name = 'hostel/hostel_list.html'
    context_object_name = 'hostels'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Hostel.objects.filter(institution=institution)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Stats for dashboard
        hostels = self.get_queryset()
        context['total_hostels'] = hostels.count()
        context['active_hostels'] = hostels.filter(is_active=True).count()
        context['inactive_hostels'] = hostels.filter(is_active=False).count()
        
        # Occupancy data
        occupancy_data = []
        for hostel in hostels:
            occupancy_data.append({
                'name': hostel.name,
                'occupancy': hostel.occupancy_percentage(),
                'available': hostel.available_beds(),
                'capacity': hostel.capacity
            })
        context['occupancy_data'] = occupancy_data
        
        return context


class HostelCreateView(DirectorRequiredMixin, CreateView):
    model = Hostel
    template_name = 'hostel/hostel_form.html'
    form_class = HostelForm
    success_url = reverse_lazy('hostel:hostel_list')
    
    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, _('Hostel created successfully!'))
        return super().form_valid(form)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        institution = get_user_institution(self.request.user)
        
        # Filter wardens to only staff from the same institution
        form.fields['warden'].queryset = form.fields['warden'].queryset.filter(
            institution=institution
        )
        form.fields['assistant_warden'].queryset = form.fields['assistant_warden'].queryset.filter(
            institution=institution
        )
        
        return form


class HostelUpdateView(DirectorRequiredMixin, UpdateView):
    model = Hostel
    template_name = 'hostel/hostel_form.html'
    form_class = HostelForm
    success_url = reverse_lazy('hostel:hostel_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Hostel updated successfully!'))
        return super().form_valid(form)
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Hostel.objects.filter(institution=institution)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        institution = get_user_institution(self.request.user)
        
        # Filter wardens to only staff from the same institution
        form.fields['warden'].queryset = form.fields['warden'].queryset.filter(
            institution=institution
        )
        form.fields['assistant_warden'].queryset = form.fields['assistant_warden'].queryset.filter(
            institution=institution
        )
        
        return form


class HostelDeleteView(DirectorRequiredMixin, DeleteView):
    model = Hostel
    template_name = 'hostel/hostel_confirm_delete.html'
    success_url = reverse_lazy('hostel:hostel_list')
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Hostel.objects.filter(institution=institution)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('Hostel deleted successfully!'))
        return super().delete(request, *args, **kwargs)


class HostelDetailView(DirectorRequiredMixin, DetailView):
    model = Hostel
    template_name = 'hostel/hostel_detail.html'
    context_object_name = 'hostel'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Hostel.objects.filter(institution=institution)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hostel = self.get_object()
        
        # Get rooms for this hostel
        rooms = hostel.rooms.all()
        context['rooms'] = rooms
        
        # Get active allocations
        active_allocations = HostelAllocation.objects.filter(
            room__hostel=hostel, 
            is_active=True
        ).select_related('student', 'room')
        context['active_allocations'] = active_allocations
        
        # Room type distribution
        room_types = rooms.values('room_type').annotate(count=Count('id'))
        context['room_types'] = room_types
        
        return context


# Room Views
class RoomListView(DirectorRequiredMixin, ListView):
    model = Room
    template_name = 'hostel/rooms/room_list.html'
    context_object_name = 'rooms'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Room.objects.filter(hostel__institution=institution).select_related('hostel')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Stats for dashboard
        rooms = self.get_queryset()
        context['total_rooms'] = rooms.count()
        context['available_rooms'] = rooms.filter(is_available=True).count()
        context['maintenance_rooms'] = rooms.filter(maintenance_required=True).count()
        
        return context


class RoomCreateView(DirectorRequiredMixin, CreateView):
    model = Room
    template_name = 'hostel/rooms/room_form.html'
    form_class = RoomForm
    success_url = reverse_lazy('hostel:room_list')
    
    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)  # <-- add this
        messages.success(self.request, _('Room created successfully!'))
        return super().form_valid(form)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        institution = get_user_institution(self.request.user)
        
        # Filter hostels to only those from the same institution
        form.fields['hostel'].queryset = form.fields['hostel'].queryset.filter(
            institution=institution
        )
        
        return form


class RoomUpdateView(DirectorRequiredMixin, UpdateView):
    model = Room
    template_name = 'hostel/rooms/room_form.html'
    form_class = RoomForm
    success_url = reverse_lazy('hostel:room_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Room updated successfully!'))
        return super().form_valid(form)
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Room.objects.filter(hostel__institution=institution)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        institution = get_user_institution(self.request.user)
        
        # Filter hostels to only those from the same institution
        form.fields['hostel'].queryset = form.fields['hostel'].queryset.filter(
            institution=institution
        )
        
        return form


class RoomDeleteView(DirectorRequiredMixin, DeleteView):
    model = Room
    template_name = 'hostel/rooms/room_confirm_delete.html'
    success_url = reverse_lazy('hostel:room_list')
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Room.objects.filter(hostel__institution=institution)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('Room deleted successfully!'))
        return super().delete(request, *args, **kwargs)


# Hostel Allocation Views
class HostelAllocationListView(DirectorRequiredMixin, ListView):
    model = HostelAllocation
    template_name = 'hostel/allocation/allocation_list.html'
    context_object_name = 'allocations'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return HostelAllocation.objects.filter(
            room__hostel__institution=institution
        ).select_related('student', 'room', 'room__hostel')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Stats for dashboard
        allocations = self.get_queryset()
        context['total_allocations'] = allocations.count()
        context['active_allocations'] = allocations.filter(is_active=True).count()
        context['expired_allocations'] = allocations.filter(
            is_active=False, 
            date_to__lt=timezone.now().date()
        ).count()
        
        return context

class HostelAllocationCreateView(DirectorRequiredMixin, CreateView):
    model = HostelAllocation
    template_name = 'hostel/allocation/allocation_form.html'
    form_class = HostelAllocationForm
    success_url = reverse_lazy('hostel:allocation_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['institution'] = get_user_institution(self.request.user)
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Add available rooms count to context for the template
        available_rooms = Room.objects.filter(
            hostel__institution=institution,
            is_available=True
        ).annotate(
            available_beds=F('capacity') - F('current_occupancy')
        ).filter(available_beds__gt=0)
        
        context['available_rooms_count'] = available_rooms.count()
        context['total_rooms'] = Room.objects.filter(hostel__institution=institution).count()
        
        return context
    
    def form_valid(self, form):
        # Double-check room capacity before saving
        room = form.cleaned_data['room']
        if room.current_occupancy >= room.capacity:
            form.add_error('room', _('This room is already at full capacity. Please select another room.'))
            return self.form_invalid(form)
        
        # Check if student already has an active allocation
        student = form.cleaned_data['student']
        if HostelAllocation.objects.filter(student=student, is_active=True).exists():
            form.add_error('student', _('This student already has an active hostel allocation.'))
            return self.form_invalid(form)
        
        allocation = form.save(commit=False)
        
        # Update room occupancy
        room.current_occupancy += 1
        room.save()
        
        # Update hostel occupancy
        hostel = room.hostel
        hostel.current_occupancy += 1
        hostel.save()
        
        messages.success(self.request, _('Hostel allocation created successfully!'))
        return super().form_valid(form)


class HostelAllocationUpdateView(DirectorRequiredMixin, UpdateView):
    model = HostelAllocation
    template_name = 'hostel/allocation/allocation_form.html'
    form_class = HostelAllocationForm
    success_url = reverse_lazy('hostel:allocation_list')
    
    def form_valid(self, form):
        old_allocation = self.get_object()
        new_room = form.cleaned_data['room']
        
        # If room changed, update occupancy counts
        if old_allocation.room != new_room:
            # Decrement old room occupancy
            old_room = old_allocation.room
            old_room.current_occupancy -= 1
            old_room.save()
            
            # Decrement old hostel occupancy
            old_hostel = old_room.hostel
            old_hostel.current_occupancy -= 1
            old_hostel.save()
            
            # Increment new room occupancy
            new_room.current_occupancy += 1
            new_room.save()
            
            # Increment new hostel occupancy
            new_hostel = new_room.hostel
            new_hostel.current_occupancy += 1
            new_hostel.save()
        
        messages.success(self.request, _('Hostel allocation updated successfully!'))
        return super().form_valid(form)
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return HostelAllocation.objects.filter(room__hostel__institution=institution)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        institution = get_user_institution(self.request.user)
        
        # Filter students to only those from the same institution
        form.fields['student'].queryset = form.fields['student'].queryset.filter(
            institution=institution
        )
        
        # Filter rooms to only those from the same institution
        form.fields['room'].queryset = form.fields['room'].queryset.filter(
            hostel__institution=institution
        )
        
        return form


class HostelAllocationDeleteView(DirectorRequiredMixin, DeleteView):
    model = HostelAllocation
    template_name = 'hostel/allocation/allocation_confirm_delete.html'
    success_url = reverse_lazy('hostel:allocation_list')
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return HostelAllocation.objects.filter(room__hostel__institution=institution)
    
    def delete(self, request, *args, **kwargs):
        allocation = self.get_object()
        
        # Update room occupancy
        room = allocation.room
        room.current_occupancy -= 1
        room.save()
        
        # Update hostel occupancy
        hostel = room.hostel
        hostel.current_occupancy -= 1
        hostel.save()
        
        messages.success(self.request, _('Hostel allocation deleted successfully!'))
        return super().delete(request, *args, **kwargs)


# Hostel Fee Structure Views
class HostelFeeStructureListView(FinanceAccessRequiredMixin, ListView):
    model = HostelFeeStructure
    template_name = 'hostel/feestructure_list.html'
    context_object_name = 'fee_structures'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return HostelFeeStructure.objects.filter(hostel__institution=institution).select_related('hostel')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fee_structures = self.get_queryset()
        
        # Stats for dashboard
        context['total_fee_structures'] = fee_structures.count()
        context['active_fee_structures'] = fee_structures.filter(is_active=True).count()
        context['inactive_fee_structures'] = fee_structures.filter(is_active=False).count()

        # Extra stats
        context['total_fee_value'] = fee_structures.aggregate(total=Sum('amount'))['total'] or 0
        context['unique_room_types'] = fee_structures.values('room_type').distinct().count()
        
        return context


class HostelFeeStructureCreateView(FinanceAccessRequiredMixin, CreateView):
    model = HostelFeeStructure
    form_class = HostelFeeStructureForm
    template_name = 'hostel/feestructure_form.html'
    success_url = reverse_lazy('hostel:feestructure_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass the institution to the form for filtering
        kwargs['institution'] = get_user_institution(self.request.user)
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _('Fee structure created successfully!'))
        return super().form_valid(form)


class HostelFeeStructureUpdateView(FinanceAccessRequiredMixin, UpdateView):
    model = HostelFeeStructure
    template_name = 'hostel/feestructure_form.html'
    form_class = HostelFeeStructureForm   
    success_url = reverse_lazy('hostel:feestructure_list')

    def form_valid(self, form):
        messages.success(self.request, _('Fee structure updated successfully!'))
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['institution'] = get_user_institution(self.request.user)  # pass institution to form
        return kwargs

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return HostelFeeStructure.objects.filter(hostel__institution=institution)


class HostelFeeStructureDeleteView(FinanceAccessRequiredMixin, DeleteView):
    model = HostelFeeStructure
    template_name = 'hostel/feestructure_confirm_delete.html'
    success_url = reverse_lazy('hostel:feestructure_list')
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return HostelFeeStructure.objects.filter(hostel__institution=institution)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('Fee structure deleted successfully!'))
        return super().delete(request, *args, **kwargs)


class HostelFeeStructureDetailView(FinanceAccessRequiredMixin, DetailView):
    model = HostelFeeStructure
    template_name = 'hostel/feestructure_detail.html'
    context_object_name = 'structure'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return HostelFeeStructure.objects.filter(hostel__institution=institution)


# Export view
class HostelExportView(DirectorRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        institution = get_user_institution(request.user)
        format_type = request.GET.get('format', 'csv')
        
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="hostels_export.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Name', 'Code', 'Type', 'Capacity', 'Current Occupancy', 
                           'Warden', 'Contact', 'Email', 'Status'])
            
            hostels = Hostel.objects.filter(institution=institution)
            for hostel in hostels:
                writer.writerow([
                    hostel.name,
                    hostel.code,
                    hostel.gender_type,
                    hostel.capacity,
                    hostel.current_occupancy,
                    hostel.warden.name if hostel.warden else '',
                    hostel.contact_number,
                    hostel.email,
                    'Active' if hostel.is_active else 'Inactive'
                ])
            
            return response
        
        # Add other formats (PDF, Excel) as needed
        return redirect('hostel:hostel_list')