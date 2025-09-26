from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db.models import Sum, Q, Count
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from xhtml2pdf import pisa
import csv
import json
from django.utils.translation import gettext_lazy as _
from .models import FeeStructure, FeeInvoice, Payment
from apps.students.models import Student
from apps.academics.models import AcademicYear, Class
from apps.core.mixins import FinanceAccessRequiredMixin
from apps.core.permissions import RoleBasedPermissionMixin
from .forms import FeeStructureForm,FeeInvoiceSearchForm,FeeInvoiceForm
from .export import FeeStructureExportView
from apps.core.utils import get_user_institution 

fee_structure_export_pdf = FeeStructureExportView.as_view()

class FeeStructureListView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, ListView):
    model = FeeStructure
    template_name = "finance/fee_structure_list.html"
    context_object_name = "fee_structures"
    required_permission = "view"  # check ROLE_PERMISSIONS['finance']

    def get_queryset(self):
        qs = super().get_queryset()
        institution = get_user_institution(self.request.user)  # Use utility function
        if institution:
            qs = qs.filter(institution=institution)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["back_url"] = self.request.META.get("HTTP_REFERER", reverse_lazy("dashboard"))
        
        institution = get_user_institution(self.request.user)  # Use utility function
        
        if institution:
            # Get fee structures counts
            fee_structures_qs = FeeStructure.objects.filter(institution=institution)
            active_fee_structures = fee_structures_qs.filter(is_active=True).count()
            inactive_fee_structures = fee_structures_qs.filter(is_active=False).count()
            total_fee_structures = fee_structures_qs.count()
            
            # Get classes and academic years
            context['classes'] = Class.objects.filter(institution=institution, is_active=True)
            context['academic_years'] = AcademicYear.objects.filter(institution=institution)
            
            # Add fee structure counts to context
            context['active_fee_structures'] = active_fee_structures
            context['inactive_fee_structures'] = inactive_fee_structures
            context['total_fee_structures'] = total_fee_structures
        else:
            context['classes'] = Class.objects.none()
            context['academic_years'] = AcademicYear.objects.none()
            context['active_fee_structures'] = 0
            context['inactive_fee_structures'] = 0
            context['total_fee_structures'] = 0
            
        return context


class FeeStructureCreateView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, CreateView):
    model = FeeStructure
    form_class = FeeStructureForm
    template_name = "finance/fee_structure_form.html"
    permission_required = "finance.add_feestructure"
    success_url = reverse_lazy("finance:fee_structure_list")

    def form_valid(self, form):
        # Use utility function to get institution
        institution = get_user_institution(self.request.user)
        if institution:
            form.instance.institution = institution
        response = super().form_valid(form)
        messages.success(
            self.request,
            _(f'Fee structure "{self.object.name}" created successfully.')
        )
        return response

    def form_invalid(self, form):
        messages.error(self.request, _("There was an error creating the fee structure. Please check the form."))
        return super().form_invalid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Use utility function to get institution
        institution = get_user_institution(self.request.user)

        if institution:
            form.fields["academic_year"].queryset = AcademicYear.objects.filter(institution=institution)
            form.fields["class_name"].queryset = Class.objects.filter(institution=institution, is_active=True)
        else:
            form.fields["academic_year"].queryset = AcademicYear.objects.none()
            form.fields["class_name"].queryset = Class.objects.none()

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["back_url"] = self.request.META.get("HTTP_REFERER", reverse_lazy("finance:fee_structure_list"))
        return context


class FeeStructureDetailView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, DetailView):
    model = FeeStructure
    template_name = 'finance/fee_structure_detail.html'
    context_object_name = 'fee_structure'
    
    def get_queryset(self):
        qs = super().get_queryset()
        institution = get_user_institution(self.request.user)
        if institution:
            qs = qs.filter(institution=institution)
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fee_structure = self.get_object()
        
        # Get institution using utility function
        institution = get_user_institution(self.request.user)
        
        if institution:
            # Count students in the class for this institution
            context['affected_students_count'] = Student.objects.filter(
                current_class=fee_structure.class_name,
                status="ACTIVE",
                institution=institution  # Add institution filter
            ).count()
            
            # Count active invoices for this fee structure and institution
            context['active_invoices_count'] = FeeInvoice.objects.filter(
                academic_year=fee_structure.academic_year,
                student__current_class=fee_structure.class_name,
                status__in=['issued', 'partial'],
                institution=institution  # Add institution filter
            ).count()
            
            # Calculate total revenue with institution filter
            context['total_revenue'] = FeeInvoice.objects.filter(
                academic_year=fee_structure.academic_year,
                student__current_class=fee_structure.class_name,
                institution=institution  # Add institution filter
            ).aggregate(total=Sum('paid_amount'))['total'] or 0
            
            # Add additional useful statistics
            context['pending_invoices_count'] = FeeInvoice.objects.filter(
                academic_year=fee_structure.academic_year,
                student__current_class=fee_structure.class_name,
                status='issued',
                institution=institution
            ).count()
            
            context['partial_payments_count'] = FeeInvoice.objects.filter(
                academic_year=fee_structure.academic_year,
                student__current_class=fee_structure.class_name,
                status='partial',
                institution=institution
            ).count()
            
            context['fully_paid_count'] = FeeInvoice.objects.filter(
                academic_year=fee_structure.academic_year,
                student__current_class=fee_structure.class_name,
                status='paid',
                institution=institution
            ).count()
        else:
            # Set default values if no institution found
            context['affected_students_count'] = 0
            context['active_invoices_count'] = 0
            context['total_revenue'] = 0
            context['pending_invoices_count'] = 0
            context['partial_payments_count'] = 0
            context['fully_paid_count'] = 0
        
        # Add back URL
        context["back_url"] = self.request.META.get(
            "HTTP_REFERER", 
            reverse_lazy("finance:fee_structure_list")
        )
        
        return context

class FeeStructureUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = FeeStructure
    form_class = FeeStructureForm
    template_name = "finance/fee_structure_form.html"
    permission_required = "finance.change_feestructure"

    def get_success_url(self):
        return reverse_lazy("finance:fee_structure_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            _(f'Fee structure "{self.object.name}" updated successfully.')
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            _("There was an error updating the fee structure. Please check the form.")
        )
        return super().form_invalid(form)

    def get_queryset(self):
        # Use utility function to get institution
        institution = get_user_institution(self.request.user)
        if institution:
            return FeeStructure.objects.filter(institution=institution)
        return FeeStructure.objects.none()

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Use utility function to get institution
        institution = get_user_institution(self.request.user)

        if institution:
            form.fields["academic_year"].queryset = AcademicYear.objects.filter(institution=institution)
            form.fields["class_name"].queryset = Class.objects.filter(institution=institution, is_active=True)
        else:
            form.fields["academic_year"].queryset = AcademicYear.objects.none()
            form.fields["class_name"].queryset = Class.objects.none()

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["back_url"] = self.request.META.get("HTTP_REFERER", reverse_lazy("finance:fee_structure_list"))
        
        # Add institution to context if needed for template
        context["institution"] = get_user_institution(self.request.user)
        
        return context



class FeeStructureDisableView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, View):
    """View to disable a fee structure"""
    
    def test_func(self):
        return self.request.user.is_superadmin or self.request.user.is_accountant
    
    def post(self, request, *args, **kwargs):
        fee_structure = get_object_or_404(FeeStructure, pk=self.kwargs['pk'])
        fee_structure.is_active = False
        fee_structure.save()
        
        messages.success(request, f'Fee structure "{fee_structure.name}" has been disabled.')
        return redirect('finance:fee_structure_detail', pk=fee_structure.pk)
    
    def get(self, request, *args, **kwargs):
        # Also allow GET requests for simplicity
        return self.post(request, *args, **kwargs)


class FeeStructureEnableView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, View):
    """View to enable a fee structure"""
    
    def test_func(self):
        return self.request.user.is_superadmin or self.request.user.is_accountant
    
    def post(self, request, *args, **kwargs):
        fee_structure = get_object_or_404(FeeStructure, pk=self.kwargs['pk'])
        fee_structure.is_active = True
        fee_structure.save()
        
        messages.success(request, f'Fee structure "{fee_structure.name}" has been enabled.')
        return redirect('finance:fee_structure_detail', pk=fee_structure.pk)
    
    def get(self, request, *args, **kwargs):
        # Also allow GET requests for simplicity
        return self.post(request, *args, **kwargs)
    
    
class FeeStructureDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = FeeStructure
    template_name = 'finance/fee_structure_confirm_delete.html'
    permission_required = 'finance.delete_feestructure'
    success_url = reverse_lazy('finance:fee_structure_list')  # Added app namespace if needed
    
    def get_queryset(self):
        # Use utility function to get institution
        institution = get_user_institution(self.request.user)
        if institution:
            return FeeStructure.objects.filter(institution=institution)
        return FeeStructure.objects.none()
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        messages.success(request, f'Fee structure "{self.object.name}" deleted successfully.')
        return redirect(success_url)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add back URL for navigation
        context["back_url"] = self.request.META.get(
            "HTTP_REFERER", 
            reverse_lazy("finance:fee_structure_list")
        )
        return context

