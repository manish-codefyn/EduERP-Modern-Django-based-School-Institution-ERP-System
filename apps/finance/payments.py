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
import json
from django.utils.translation import gettext_lazy as _
from .models import FeeStructure, FeeInvoice, Payment
from apps.students.models import Student
from apps.academics.models import AcademicYear, Class
from apps.core.mixins import FinanceAccessRequiredMixin
from apps.core.permissions import RoleBasedPermissionMixin
from .forms import PaymentForm
import csv
from io import StringIO
from utils.utils import render_to_pdf, export_pdf_response
from apps.core.utils import get_user_institution 
from .export import PaymentExportView,PaymentDetailExportView
 
payment_list_export = PaymentExportView.as_view()
payment_detail_export = PaymentDetailExportView.as_view()

class PaymentListView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, ListView):
    model = Payment
    template_name = 'finance/payments/payment_list.html'
    permission_required = 'finance.view_payment'
    context_object_name = 'payments'
    paginate_by = 20
    
    def get_queryset(self):
        # Get user's institution
        institution = get_user_institution(self.request.user, request=self.request)
        
        queryset = Payment.objects.all()
        
        # Filter by institution
        if institution:
            queryset = queryset.filter(institution=institution)

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by payment mode
        payment_mode = self.request.GET.get('payment_mode')
        if payment_mode:
            queryset = queryset.filter(payment_mode=payment_mode)

        # Filter by student name or ID
        student_query = self.request.GET.get('student')
        if student_query:
            queryset = queryset.filter(
                Q(student__user__first_name__icontains=student_query) |
                Q(student__user__last_name__icontains=student_query) |
                Q(student__roll_number__icontains=student_query) |
                Q(student__admission_number__icontains=student_query)
            )

        # Filter by invoice number
        invoice_query = self.request.GET.get('invoice')
        if invoice_query:
            queryset = queryset.filter(invoice__invoice_number__icontains=invoice_query)

        # Filter by payment number
        payment_number = self.request.GET.get('payment_number')
        if payment_number:
            queryset = queryset.filter(payment_number__icontains=payment_number)

        # Date range filtering
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date:
            queryset = queryset.filter(payment_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(payment_date__lte=end_date)

        return queryset.select_related(
            'invoice__student__user', 
            'student__user', 
            'institution'
        ).order_by('-payment_date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter choices to context
        context['status_choices'] = Payment.STATUS_CHOICES
        context['mode_choices'] = Payment.MODE_CHOICES
        
        # Add current filter values to context for template
        context['current_filters'] = {
            'status': self.request.GET.get('status', ''),
            'payment_mode': self.request.GET.get('payment_mode', ''),
            'student': self.request.GET.get('student', ''),
            'invoice': self.request.GET.get('invoice', ''),
            'payment_number': self.request.GET.get('payment_number', ''),
            'start_date': self.request.GET.get('start_date', ''),
            'end_date': self.request.GET.get('end_date', ''),
        }
        
        # Add stats for dashboard
        institution = get_user_institution(self.request.user, request=self.request)
        if institution:
            payments = Payment.objects.filter(institution=institution)
            context['total_payments'] = payments.count()
            context['total_revenue'] = payments.aggregate(
                total=Sum('amount_paid')
            )['total'] or 0
            context['completed_payments'] = payments.filter(
                status__in=['completed', 'paid']
            ).count()
        
        return context

class PaymentCreateView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'finance/payments/payment_form.html'
    permission_required = 'finance.add_payment'

    def get_success_url(self):
        return reverse_lazy('finance:fee_invoice_detail', kwargs={'pk': self.object.invoice.pk})

    def get_form_kwargs(self):
        """Pass request to form for pre-filling"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        # institution assignment
        institution = None

        if hasattr(self.request.user, "profile") and getattr(self.request.user.profile, "institution", None):
            institution = self.request.user.profile.institution
        elif hasattr(self.request.user, "student_profile") and getattr(self.request.user.student_profile, "institution", None):
            institution = self.request.user.student_profile.institution
        elif form.cleaned_data.get("invoice"):
            institution = form.cleaned_data["invoice"].institution

        if not institution:
            messages.error(self.request, "Your account is not linked to any institution.")
            return self.form_invalid(form)

        form.instance.institution = institution
        form.instance.status = "completed"

        # Check invoice balance
        invoice = form.cleaned_data["invoice"]
        amount = form.cleaned_data["amount"]
        balance = invoice.total_amount - invoice.paid_amount
        if amount > balance:
            form.add_error("amount", f"Amount cannot exceed outstanding balance of {balance}")
            messages.error(self.request, f" Payment failed: Amount {amount} exceeds outstanding balance ({balance}).")
            return self.form_invalid(form)

        response = super().form_valid(form)
        messages.success(self.request, f"Payment #{self.object.payment_number} created successfully.")
        return response

    def form_invalid(self, form):
        """Show error when form is invalid"""
        messages.error(self.request, "There were errors in your submission. Please correct them and try again.")
        return super().form_invalid(form)



class PaymentDetailView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, DetailView):
    model = Payment
    template_name = 'finance/payments/payment_receipt.html'
    permission_required = 'finance.view_payment'
    
    def get_queryset(self):
        return Payment.objects.filter(school=self.request.school)
    
    def get(self, request, *args, **kwargs):
        payment = self.get_object()
        
        if request.GET.get('format') == 'pdf':
            context = {
                'payment': payment,
                'school': request.school,
                'date': timezone.now().date(),
            }
            
            html_string = render_to_string('finance/payment_receipt_pdf.html', context)
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="receipt-{payment.payment_number}.pdf"'
            
            pisa_status = pisa.CreatePDF(html_string, dest=response, encoding='utf-8')
            if pisa_status.err:
                return HttpResponse("Error generating PDF", status=500)
            
            return response
        
        return super().get(request, *args, **kwargs)


class PaymentDetailView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, DetailView):
    model = Payment
    template_name = 'finance/payments/payment_detail.html'
    permission_required = 'finance.view_payment'
    context_object_name = 'payment'

    def get_queryset(self):
        queryset = super().get_queryset()
        institution = get_user_institution(self.request.user, self.request)
        if institution:
            queryset = queryset.filter(institution=institution)
        return queryset.select_related(
            'invoice__student__user',
            'student__user',
            'institution'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Payment Details - #{self.object.payment_number}"
        return context
    
    
class PaymentUpdateView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'finance/payments/payment_update_form.html'  # Use the same template
    permission_required = 'finance.change_payment'
    context_object_name = 'payment'

    def get_success_url(self):
        messages.success(self.request, f"Payment #{self.object.payment_number} updated successfully.")
        return reverse_lazy('finance:payment_list')

    def get_form_kwargs(self):
        """Pass request to form for pre-filling"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Edit Payment - #{self.object.payment_number}"
        context['back_url'] = reverse_lazy('finance:payment_detail', kwargs={'pk': self.object.pk})
        context['editing'] = True  # Flag to indicate we're in edit mode
        return context

    def form_valid(self, form):
        # Handle status changes and validations
        old_status = self.object.status
        new_status = form.cleaned_data.get('status')
        
        # Prevent changing status from completed/paid/refunded/cancelled
        if old_status in ['completed', 'paid', 'refunded', 'cancelled'] and new_status != old_status:
            form.add_error('status', f"Cannot change status from {self.object.get_status_display()}")
            messages.error(self.request, f"Cannot change status from {self.object.get_status_display()}")
            return self.form_invalid(form)
        
        # For existing payments, don't allow changing the amount
        if form.cleaned_data.get('amount') != self.object.amount:
            form.add_error('amount', 'Cannot change payment amount for existing payments')
            messages.error(self.request, 'Cannot change payment amount for existing payments')
            return self.form_invalid(form)
        
        response = super().form_valid(form)
        return response

    def form_invalid(self, form):
        """Show error when form is invalid"""
        messages.error(self.request, "There were errors in your submission. Please correct them and try again.")
        return super().form_invalid(form)

class PaymentDeleteView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, DeleteView):
    model = Payment
    template_name = 'finance/payments/payment_confirm_delete.html'
    permission_required = 'finance.delete_payment'
    success_url = reverse_lazy('finance:payment_list')
    context_object_name = 'payment'

    def get_queryset(self):
        queryset = super().get_queryset()
        institution = get_user_institution(self.request.user, self.request)
        if institution:
            queryset = queryset.filter(institution=institution)
        return queryset

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        payment_number = self.object.payment_number
        
        # Check if payment can be deleted (only allow deletion of certain statuses)
        if self.object.status in ['completed', 'paid', 'refunded']:
            messages.error(request, f"Cannot delete payment #{payment_number} with status '{self.object.get_status_display()}'")
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f"Cannot delete payment with status '{self.object.get_status_display()}'"
                })
            return super().get(request, *args, **kwargs)
        
        success_message = f"Payment #{payment_number} has been deleted successfully."
        self.object.delete()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': success_message
            })
        
        messages.success(request, success_message)
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Delete Payment - #{self.object.payment_number}"
        return context

class PaymentRefundView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, UpdateView):
    model = Payment
    fields = ['refund_amount', 'refund_reason']
    template_name = 'finance/payments/payment_refund.html'
    permission_required = 'finance.change_payment'
    
    def get_success_url(self):
        return reverse_lazy('payment_list')
    
    def form_valid(self, form):
        payment = form.save(commit=False)
        refund_amount = form.cleaned_data['refund_amount']
        
        if refund_amount > payment.amount:
            form.add_error('refund_amount', 'Refund amount cannot exceed original payment amount')
            return self.form_invalid(form)
        
        payment.status = 'refunded'
        payment.save()
        
        payment.invoice.paid_amount -= refund_amount
        payment.invoice.save()
        
        messages.success(self.request, f'Payment #{payment.payment_number} refunded successfully.')
        return super().form_valid(form)
    
    def get_queryset(self):
        return Payment.objects.filter(school=self.request.school, status='completed')


class PaymentExportView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, View):
    """
    Export Payments with filters:
    - class_id: Filter by class
    - academic_year_id: Filter by academic year
    - payment_status: Filter by status (paid, pending, failed, etc.)
    - Only for payments in the user's institution
    """

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        class_id = request.GET.get("class_id")
        academic_year_id = request.GET.get("academic_year_id")
        payment_status = request.GET.get("payment_status")

        # Base queryset filtered by institution
        institution = getattr(request.user.profile, "institution", None)
        if not institution:
            return HttpResponse("No institution associated with your account", status=400)

        payments_qs = Payment.objects.filter(institution=institution)

        # Apply filters
        filters = Q()

        if class_id:
            filters &= Q(student__current_class_id=class_id)
            class_obj = get_object_or_404(Class, id=class_id, institution=institution)
        else:
            class_obj = None

        if academic_year_id:
            filters &= Q(academic_year_id=academic_year_id)
            academic_year_obj = get_object_or_404(AcademicYear, id=academic_year_id, institution=institution)
        else:
            academic_year_obj = None

        if payment_status:
            filters &= Q(status=payment_status)

        payments_qs = payments_qs.filter(filters).order_by("-created_at")

        # Build filename
        filename_parts = ["payments"]
        if class_obj:
            filename_parts.append(f"Class_{class_obj.name}")
        if academic_year_obj:
            filename_parts.append(f"Year_{academic_year_obj.name}")
        if payment_status:
            filename_parts.append(payment_status.capitalize())

        filename = "_".join(filename_parts)

        # Build rows
        rows = []
        for pay in payments_qs:
            rows.append({
                "student": str(pay.student),
                "class_name": str(getattr(pay.student.current_class, "name", "")),
                "academic_year": str(pay.academic_year),
                "amount": f"{pay.amount:.2f}",
                "method": pay.payment_method,
                "status": pay.status,
                "transaction_id": pay.transaction_id or "",
                "date": pay.created_at.strftime("%Y-%m-%d %H:%M"),
            })

        # Handle empty results
        if not rows:
            if fmt == "pdf":
                context = {
                    "payments": [],
                    "generated_date": timezone.now(),
                    "class_obj": class_obj,
                    "academic_year_obj": academic_year_obj,
                    "status_filter": payment_status,
                    "no_data": True,
                    "organization": institution,
                }
                pdf_bytes = render_to_pdf("finance/export/payments_pdf.html", context)
                if pdf_bytes:
                    return export_pdf_response(pdf_bytes, f"{filename}.pdf")
                return HttpResponse("Error generating PDF", status=500)
            return HttpResponse("No payments found for the selected filters", status=404)

        # CSV Export
        if fmt == "csv":
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["Student", "Class", "Academic Year", "Amount", "Method", "Status", "Transaction ID", "Date"])
            for r in rows:
                writer.writerow([r["student"], r["class_name"], r["academic_year"], r["amount"], r["method"], r["status"], r["transaction_id"], r["date"]])
            resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
            return resp

        # PDF Export
        elif fmt == "pdf":
            context = {
                "payments": rows,
                "generated_date": timezone.now(),
                "class_obj": class_obj,
                "academic_year_obj": academic_year_obj,
                "status_filter": payment_status,
                "organization": institution,
                "logo": getattr(institution.logo, 'url', None) if institution else None,
                "stamp": getattr(institution.stamp, 'url', None) if institution else None,
            }
            pdf_bytes = render_to_pdf("finance/export/payments_pdf.html", context)
            if pdf_bytes:
                return export_pdf_response(pdf_bytes, f"{filename}.pdf")
            return HttpResponse("Error generating PDF", status=500)

        # Excel Export
        elif fmt == "excel":
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["Student", "Class", "Academic Year", "Amount", "Method", "Status", "Transaction ID", "Date"])
            for r in rows:
                writer.writerow([r["student"], r["class_name"], r["academic_year"], r["amount"], r["method"], r["status"], r["transaction_id"], r["date"]])
            resp = HttpResponse(buffer.getvalue(), content_type="application/vnd.ms-excel")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.xls"'
            return resp

        return HttpResponse("Invalid export format", status=400)




class StudentInvoicesAjaxView(View):
    def get(self, request, student_id):
        try:
            student = Student.objects.get(pk=student_id)
            invoices = FeeInvoice.objects.filter(student=student, status__in=['issued', 'partial'])
            
            invoice_data = []
            for invoice in invoices:
                balance = invoice.total_amount - invoice.paid_amount
                if balance > 0:  # Only include invoices with outstanding balance
                    invoice_data.append({
                        'id': invoice.id,
                        'invoice_number': invoice.invoice_number,
                        'total_amount': float(invoice.total_amount),
                        'paid_amount': float(invoice.paid_amount),
                        'balance': float(balance),
                        'due_date': invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else None
                    })
            
            return JsonResponse({
                'success': True,
                'student_id': student.id,
                'student_name': str(student),
                'invoices': invoice_data
            })
        except Student.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Student not found'})
        
class InvoiceAjaxView(View):
    def get(self, request, pk):
        try:
            invoice = FeeInvoice.objects.get(pk=pk)
            data = {
                'success': True,
                'total_amount': float(invoice.total_amount),
                'paid_amount': float(invoice.paid_amount),
                'student_id': invoice.student.id,
                'student_name': str(invoice.student),
                'balance': float(invoice.total_amount - invoice.paid_amount)
            }
            return JsonResponse(data)
        except FeeInvoice.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invoice not found'})

