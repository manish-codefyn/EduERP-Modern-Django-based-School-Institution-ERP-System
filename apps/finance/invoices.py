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
from .forms import FeeStructureForm,FeeInvoiceSearchForm,FeeInvoiceForm,PaymentForm
from .export import FeeStructureExportView
from apps.core.utils import get_user_institution
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import uuid
from .export import FeeInvoiceExportView,FeeInvoiceDetailExportView


fee_invoice_list_export = FeeInvoiceExportView.as_view()
fee_invoice_detail_export = FeeInvoiceDetailExportView.as_view()

# ---------------- Fee Invoice List ----------------



class FeeInvoiceListView(ListView):
    model = FeeInvoice
    template_name = 'finance/invoices/fee_invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = FeeInvoice.objects.filter(institution=self.request.user.profile.institution)
        
        # Get filter parameters from request
        status = self.request.GET.get('status')
        student_id = self.request.GET.get('student')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        # Apply filters
        if status:
            queryset = queryset.filter(status=status)
        
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        if start_date:
            queryset = queryset.filter(issue_date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(issue_date__lte=end_date)
        
        # Prefetch related data for performance
        queryset = queryset.select_related(
            'student', 
            'student__current_class', 
            'academic_year'
        )
        
        return queryset.order_by('-issue_date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        institution = self.request.user.profile.institution

        # Add status choices for filter dropdown
        context['status_choices'] = FeeInvoice.STATUS_CHOICES

        # Add students for filter dropdown
        context['students'] = Student.objects.filter(
            institution=institution
        ).order_by('roll_number')

        #Rebuild full queryset (not paginated) for statistics
        full_qs = FeeInvoice.objects.filter(institution=institution)

        status = self.request.GET.get('status')
        student_id = self.request.GET.get('student')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if status:
            full_qs = full_qs.filter(status=status)
        if student_id:
            full_qs = full_qs.filter(student_id=student_id)
        if start_date:
            full_qs = full_qs.filter(issue_date__gte=start_date)
        if end_date:
            full_qs = full_qs.filter(issue_date__lte=end_date)

        # Calculate statistics on full queryset
        context['total_count'] = full_qs.count()
        context['paid_count'] = full_qs.filter(status='paid').count()
        context['pending_count'] = full_qs.filter(status__in=['issued', 'partial']).count()

        today = timezone.now().date()
        context['overdue_count'] = full_qs.filter(
            status='issued',
            due_date__lt=today
        ).count()

        # Pass filter values back to template
        context['current_filters'] = {
            'status': self.request.GET.get('status', ''),
            'student': self.request.GET.get('student', ''),
            'start_date': self.request.GET.get('start_date', ''),
            'end_date': self.request.GET.get('end_date', ''),
        }

        return context


@login_required
def get_students_by_class(request):
    class_id = request.GET.get('class')
    institution = getattr(request.user.profile, 'institution', None)

    if not class_id or not institution:
        return JsonResponse({'students': []})

    students = Student.objects.filter(
        current_class_id=class_id,
        institution=institution,
        status='ACTIVE'
    ).values('id', 'first_name', 'last_name')

    students_list = [{'id': s['id'], 'full_name': f"{s['first_name']} {s['last_name']}"} for s in students]
    return JsonResponse({'students': students_list})


# ---------------- Fee Invoice Create ----------------


class FeeInvoiceCreateView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, TemplateView):
    template_name = 'finance/invoices/fee_invoice_form.html'
    permission_required = 'finance.add_feeinvoice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user, request=self.request)

        if not institution:
            context['academic_years'] = []
            context['classes'] = []
            context['fee_structures'] = []
            context['students'] = []
            return context

        context['academic_years'] = AcademicYear.objects.filter(institution=institution)
        context['classes'] = Class.objects.filter(institution=institution, is_active=True)
        context['fee_structures'] = FeeStructure.objects.filter(institution=institution, is_active=True)
        context['students'] = Student.objects.filter(institution=institution, status='ACTIVE').values(
            'id', 'first_name', 'last_name', 'roll_number', 'current_class_id'
        )
        return context

    def post(self, request, *args, **kwargs):
        institution = get_user_institution(self.request.user, request=self.request)
        if not institution:
            return redirect('finance:fee_invoice_create')

        try:
            fee_structure_id = request.POST.get('fee_structure')
            academic_year_id = request.POST.get('academic_year')
            student_ids = [s for s in request.POST.getlist('students') if s]

            if not fee_structure_id or not student_ids or not academic_year_id:
                messages.error(request, "Please select fee structure, academic year, and students.")
                return redirect('finance:fee_invoice_create')

            fee_structure = FeeStructure.objects.get(id=fee_structure_id, institution=institution)
            academic_year = AcademicYear.objects.get(id=academic_year_id, institution=institution)
            
            students = Student.objects.filter(
                id__in=student_ids,
                institution=institution,
                status='ACTIVE'
            )

            results = {
                'created': [],
                'exists': [],
                'wrong_class': [],
                'inactive': []
            }

            for student in students:
                # Check if student is in the correct class
                if student.current_class != fee_structure.class_name:
                    results['wrong_class'].append(
                        f"{student.full_name} (Current class: {student.current_class.name})"
                    )
                    continue

                # Check if student is active
                if student.status != 'ACTIVE':
                    results['inactive'].append(student.full_name)
                    continue

                # Check if invoice already exists
                existing_invoice = FeeInvoice.objects.filter(
                    institution=institution,
                    student=student,
                    academic_year=academic_year
                ).first()

                if existing_invoice:
                    results['exists'].append(
                        f"{student.full_name} (Invoice: {existing_invoice.invoice_number})"
                    )
                else:
                    # Create new invoice
                    invoice = FeeInvoice.objects.create(
                        institution=institution,
                        student=student,
                        academic_year=academic_year,
                        total_amount=fee_structure.amount,
                        issue_date=timezone.now().date(),
                        due_date=timezone.now().date() + timezone.timedelta(days=30),
                        status='issued'
                    )
                    results['created'].append(
                        f"{student.full_name} (Invoice: {invoice.invoice_number})"
                    )

            # Generate appropriate messages
            if results['created']:
                success_msg = f"Created {len(results['created'])} invoice(s). "
                if len(results['created']) <= 5:
                    success_msg += "Students: " + ", ".join(results['created'])
                else:
                    success_msg += f"First 5: {', '.join(results['created'][:5])} and {len(results['created']) - 5} more."
                messages.success(request, success_msg)

            if results['exists']:
                warning_msg = f"{len(results['exists'])} invoice(s) already exist. "
                if len(results['exists']) <= 3:
                    warning_msg += "Students: " + ", ".join(results['exists'])
                else:
                    warning_msg += f"Examples: {', '.join(results['exists'][:3])} and {len(results['exists']) - 3} more."
                messages.warning(request, warning_msg)

            if results['wrong_class']:
                error_msg = f"{len(results['wrong_class'])} student(s) not in correct class. "
                if len(results['wrong_class']) <= 3:
                    error_msg += "Students: " + ", ".join(results['wrong_class'])
                else:
                    error_msg += f"Examples: {', '.join(results['wrong_class'][:3])} and {len(results['wrong_class']) - 3} more."
                messages.error(request, error_msg)

            if results['inactive']:
                error_msg = f"{len(results['inactive'])} student(s) are inactive. "
                if len(results['inactive']) <= 3:
                    error_msg += "Students: " + ", ".join(results['inactive'])
                else:
                    error_msg += f"Examples: {', '.join(results['inactive'][:3])} and {len(results['inactive']) - 3} more."
                messages.error(request, error_msg)

            if not any(results.values()):
                messages.info(request, "No actions were taken. Please check your selections.")

            return redirect('finance:fee_invoice_list')

        except FeeStructure.DoesNotExist:
            messages.error(request, "Selected fee structure does not exist.")
            return redirect('finance:fee_invoice_create')
        except AcademicYear.DoesNotExist:
            messages.error(request, "Selected academic year does not exist.")
            return redirect('finance:fee_invoice_create')
        except Exception as e:
            messages.error(request, f"Error generating invoices: {str(e)}")
            return redirect('finance:fee_invoice_create')

class FeeInvoiceDetailView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, DetailView):
    model = FeeInvoice
    template_name = 'finance/invoices/fee_invoice_detail.html'
    permission_required = 'finance.view_feeinvoice'
    context_object_name = 'invoice'
    

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return FeeInvoice.objects.filter(institution=institution)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Order payments newest → oldest
        context['payments'] = self.object.payments.all().order_by('-payment_date')
        # Pass the latest payment for receipt download
        context['latest_payment'] = context['payments'].first()
        return context


class FeeInvoiceUpdateView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, UpdateView):
    model = FeeInvoice
    form_class = FeeInvoiceForm
    template_name = 'finance/invoices/fee_invoice_update_form.html'
    permission_required = 'finance.change_feeinvoice'
    context_object_name = 'invoice'

    def get_queryset(self):
        institution = get_user_institution(self.request.user, request=self.request)
        if institution:
            return FeeInvoice.objects.filter(institution=institution)
        return FeeInvoice.objects.none()

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        institution = get_user_institution(self.request.user, request=self.request)
        
        # Disable certain fields for editing
        form.fields['student'].disabled = True
        form.fields['academic_year'].disabled = True
        form.fields['institution'].disabled = True
        
        # Set querysets for fields
        if institution:
            form.fields['student'].queryset = Student.objects.filter(institution=institution)
            form.fields['academic_year'].queryset = AcademicYear.objects.filter(institution=institution)
        else:
            form.fields['student'].queryset = Student.objects.none()
            form.fields['academic_year'].queryset = AcademicYear.objects.none()
            
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user, request=self.request)
        
        if not institution:
            return context

        # Add payment history
        context['payments'] = self.object.payments.all().order_by('-payment_date')
        
        # Add student details
        context['student'] = self.object.student
        
        # Add available payment modes
        context['payment_modes'] = Payment.MODE_CHOICES
        
        # Add payment form for quick payment creation
        context['payment_form'] = PaymentForm(initial={
            'invoice': self.object,
            'student': self.object.student,
            'institution': institution,
            'amount': self.object.balance,
            'amount_paid': self.object.balance
        })
        
        return context

    def form_valid(self, form):
        # Calculate status based on paid amount
        instance = form.instance
        if instance.paid_amount >= instance.total_amount:
            instance.status = 'paid'
        elif instance.paid_amount > 0:
            instance.status = 'partial'
        else:
            instance.status = 'issued'
        
        messages.success(self.request, f'Invoice #{instance.invoice_number} updated successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('finance:fee_invoice_detail', kwargs={'pk': self.object.pk})


class FeeInvoiceDeleteView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, DeleteView):
    model = FeeInvoice
    template_name = 'finance/invoices/fee_invoice_confirm_delete.html'
    permission_required = 'finance.delete_feeinvoice'
    success_url = reverse_lazy('fee_invoice_list')
    
    def get_queryset(self):
        return FeeInvoice.objects.filter(school=self.request.school)
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        
        if self.object.payments.exists():
            messages.error(request, 'Cannot delete invoice with existing payments.')
            return redirect(success_url)
        
        self.object.delete()
        messages.success(request, f'Fee invoice #{self.object.invoice_number} deleted successfully.')
        return redirect(success_url)


