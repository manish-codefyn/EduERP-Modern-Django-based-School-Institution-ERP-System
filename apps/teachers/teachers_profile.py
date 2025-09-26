from django.views.generic import DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404

from ..users.models import Teacher

class TeacherProfileView(LoginRequiredMixin, DetailView):
    """View for teachers to see their own profile"""
    model = Teacher
    template_name = 'teachers/teacher_profile.html'
    context_object_name = 'teacher'
    
    def get_object(self):
        # Ensure user can only view their own profile
        return get_object_or_404(Teacher, user=self.request.user)

class TeacherProfileUpdateView(LoginRequiredMixin, UpdateView):
    """View for teachers to edit their own profile"""
    model = Teacher
    template_name = 'teachers/teacher_profile_edit.html'
    fields = [
        'photo', 'first_name', 'middle_name', 'last_name', 'email', 
        'mobile', 'dob', 'gender', 'blood_group', 'address',
        'emergency_contact', 'emergency_contact_name'
    ]
    
    def get_object(self):
        # Ensure user can only edit their own profile
        return get_object_or_404(Teacher, user=self.request.user)
    
    def get_success_url(self):
        messages.success(self.request, 'Profile updated successfully!')
        return reverse_lazy('teachers:teacher_profile')
    
    def form_valid(self, form):
        # Ensure the user field is not changed
        form.instance.user = self.request.user
        return super().form_valid(form)

class TeacherIDCardView(LoginRequiredMixin, DetailView):
    """View for teachers to download their ID card"""
    model = Teacher
    template_name = 'teachers/teacher_id_card.html'
    
    def get_object(self):
        return get_object_or_404(Teacher, user=self.request.user)
    
    def get(self, request, *args, **kwargs):
        # You can implement PDF generation here
        teacher = self.get_object()
        # For now, just show the ID card template