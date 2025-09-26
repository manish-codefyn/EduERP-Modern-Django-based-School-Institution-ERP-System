# views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Count
from .models import HostelFacility
from .forms import HostelFacilityForm
from apps.core.utils import get_user_institution
from apps.core.mixins import StudentManagementRequiredMixin,DirectorRequiredMixin


class HostelFacilityListView(StudentManagementRequiredMixin, ListView):
    model = HostelFacility
    template_name = 'hostel/facility/facility_list.html'
    context_object_name = 'facilities'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_facilities'] = HostelFacility.objects.count()
        context['most_common_icon'] = HostelFacility.objects.values('icon').annotate(
            count=Count('icon')
        ).order_by('-count').first()
        return context
    
    
class HostelFacilityCreateView( StudentManagementRequiredMixin, CreateView):
    model = HostelFacility
    form_class = HostelFacilityForm
    template_name = 'hostel/facility/facility_form.html'
    success_url = reverse_lazy('hostel:facility_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Facility'
        context['submit_text'] = 'Create Facility'
        context['common_icons'] = [
            ('wifi', 'WiFi'),
            ('tv', 'TV'),
            ('snow', 'AC'),
            ('droplet', 'Water'),
            ('lightning', 'Power'),
            ('shield', 'Security'),
            ('trash', 'Cleaning'),
            ('cup', 'Kitchen'),
            ('car', 'Parking'),
            ('lock', 'Lock'),
            ('thermometer', 'Heating'),
            ('fan', 'Fan'),
            ('lamp', 'Lighting'),
            ('phone', 'Phone'),
            ('wifi-off', 'No WiFi'),
        ]
        return context
    
    def form_valid(self, form):
        # Automatically set the institution based on the logged-in user
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, 'Facility created successfully!')
        return super().form_valid(form)


class HostelFacilityUpdateView( StudentManagementRequiredMixin, UpdateView):
    model = HostelFacility
    form_class = HostelFacilityForm
    template_name = 'hostel/facility/facility_form.html'
    success_url = reverse_lazy('hostel:facility_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Facility'
        context['submit_text'] = 'Update Facility'
        context['common_icons'] = [
            ('wifi', 'WiFi'),
            ('tv', 'TV'),
            ('snow', 'AC'),
            ('droplet', 'Water'),
            ('lightning', 'Power'),
            ('shield', 'Security'),
            ('trash', 'Cleaning'),
            ('cup', 'Kitchen'),
            ('car', 'Parking'),
            ('lock', 'Lock'),
            ('thermometer', 'Heating'),
            ('fan', 'Fan'),
            ('lamp', 'Lighting'),
            ('phone', 'Phone'),
            ('wifi-off', 'No WiFi'),
        ]
        return context
    
    def form_valid(self, form):
        # Automatically set the institution based on the logged-in user
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, 'Facility created successfully!')
        return super().form_valid(form)



    
class HostelFacilityDeleteView( DirectorRequiredMixin, DeleteView):
    model = HostelFacility
    template_name = 'hostel/facility/facility_confirm_delete.html'
    success_url = reverse_lazy('hostel:facility_list')
    
    def get_queryset(self):
        # Ensure users can only delete facilities in their institution
        institution = get_user_institution(self.request.user)
        return HostelFacility.objects.filter(institution=institution)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Facility deleted successfully!')
        return super().delete(request, *args, **kwargs)