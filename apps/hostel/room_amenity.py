from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Count
from .models import RoomAmenity
from .forms import RoomAmenityForm
from apps.core.utils import get_user_institution
from apps.core.mixins import StudentManagementRequiredMixin,DirectorRequiredMixin



class RoomAmenityListView(StudentManagementRequiredMixin, ListView):
    model = RoomAmenity
    template_name = 'hostel/room_amenity/amenity_list.html'
    context_object_name = 'amenities'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return RoomAmenity.objects.filter(institution=institution).order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        context['total_amenities'] = RoomAmenity.objects.filter(institution=institution).count()
        return context


class RoomAmenityCreateView( StudentManagementRequiredMixin, CreateView):
    model = RoomAmenity
    form_class = RoomAmenityForm
    template_name = 'hostel/room_amenity/amenity_form.html'
    success_url = reverse_lazy('hostel:amenity_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request  # Pass request to form for institution check
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Room Amenity'
        context['submit_text'] = 'Create Amenity'
        return context
    
    def form_valid(self, form):
        # Automatically set the institution based on the logged-in user
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, 'Room amenity created successfully!')
        return super().form_valid(form)


class RoomAmenityUpdateView( StudentManagementRequiredMixin, UpdateView):
    model = RoomAmenity
    form_class = RoomAmenityForm
    template_name = 'hostel/room_amenity/amenity_form.html'
    success_url = reverse_lazy('hostel:amenity_list')
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return RoomAmenity.objects.filter(institution=institution)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request  # Pass request to form for institution check
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Room Amenity'
        context['submit_text'] = 'Update Amenity'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Room amenity updated successfully!')
        return super().form_valid(form)


class RoomAmenityDeleteView( DirectorRequiredMixin, DeleteView):
    model = RoomAmenity
    template_name = 'hostel/room_amenity/amenity_confirm_delete.html'
    success_url = reverse_lazy('hostel:amenity_list')
    
    def get_queryset(self):
        # Ensure users can only delete amenities in their institution
        institution = get_user_institution(self.request.user)
        return RoomAmenity.objects.filter(institution=institution)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Room amenity deleted successfully!')
        return super().delete(request, *args, **kwargs)