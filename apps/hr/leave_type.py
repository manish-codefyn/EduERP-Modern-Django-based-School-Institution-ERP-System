from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from apps.core.mixins import StaffManagementRequiredMixin, DirectorRequiredMixin
from apps.core.utils import get_user_institution
from .models import LeaveType
from .forms import LeaveTypeForm

class LeaveTypeListView( DirectorRequiredMixin, ListView):
    model = LeaveType
    template_name = 'hr/leave/leave_type_list.html'
    context_object_name = 'leave_types'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        institute = get_user_institution(self.request.user)
        
        # Filter by institute if applicable
        if institute:
            queryset = queryset.filter(institution=institute)
        
        # Filter by active status
        is_active = self.request.GET.get('is_active')
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query)
            )
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        
        # Add statistics for the dashboard cards
        context['total_leave_types'] = queryset.count()
        context['active_leave_types'] = queryset.filter(is_active=True).count()
        context['carry_forward_types'] = queryset.filter(carry_forward=True).count()
        context['approval_required_types'] = queryset.filter(requires_approval=True).count()
        
        return context

class LeaveTypeCreateView( DirectorRequiredMixin, CreateView):
    model = LeaveType
    form_class = LeaveTypeForm
    template_name = 'hr/leave/leave_type_form.html'
    success_url = reverse_lazy('hr:leave_type_list')
    
    def form_valid(self, form):
        institution = get_user_institution(self.request.user)
        if not institution:
            messages.error(self.request, "You must be associated with an institution to create leave types.")
            return redirect(self.success_url)
        
        form.instance.institution = institution
        messages.success(self.request, f"Leave type '{form.instance.name}' created successfully.")
        return super().form_valid(form)

class LeaveTypeUpdateView( DirectorRequiredMixin, UpdateView):
    model = LeaveType
    form_class = LeaveTypeForm
    template_name = 'hr/leave/leave_type_form.html'
    success_url = reverse_lazy('hr:leave_type_list')
    
    def form_valid(self, form):
        messages.success(self.request, f"Leave type '{form.instance.name}' updated successfully.")
        return super().form_valid(form)

class LeaveTypeDetailView( DirectorRequiredMixin, DetailView):
    model = LeaveType
    template_name = 'hr/leave/leave_type_detail.html'
    context_object_name = 'leave_type'

class LeaveTypeDeleteView( DirectorRequiredMixin, DeleteView):
    model = LeaveType
    template_name = 'hr/leave/leave_type_confirm_delete.html'
    success_url = reverse_lazy('hr:leave_type_list')
    
    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, f"Leave type '{obj.name}' deleted successfully.")
        return super().delete(request, *args, **kwargs)