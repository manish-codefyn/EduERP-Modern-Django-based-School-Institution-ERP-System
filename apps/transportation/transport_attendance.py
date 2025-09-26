# transport/views/attendance.py
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import StaffManagementRequiredMixin
from .models import TransportAttendance
from .forms import TransportAttendanceForm
from apps.core.utils import get_user_institution

class TransportAttendanceListView( StaffManagementRequiredMixin, ListView):
    model = TransportAttendance
    template_name = 'transport/attendance/attendance_list.html'
    context_object_name = 'attendances'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = TransportAttendance.objects.filter(institution=institution).order_by('-date')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(student_transport__student__name__icontains=search)
        return queryset

class TransportAttendanceCreateView( StaffManagementRequiredMixin, CreateView):
    model = TransportAttendance
    form_class = TransportAttendanceForm
    template_name = 'transport/attendance/attendance_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        form.instance.recorded_by = self.request.user
        messages.success(self.request, "Attendance recorded successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('transport:attendance_list')

class TransportAttendanceUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = TransportAttendance
    form_class = TransportAttendanceForm
    template_name = 'transport/attendance/attendance_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Attendance updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('transport:attendance_list')

class TransportAttendanceDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = TransportAttendance
    template_name = 'transport/attendance/attendance_confirm_delete.html'
    success_url = reverse_lazy('transport:attendance_list')

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return TransportAttendance.objects.filter(institution=institution)
