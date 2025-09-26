
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


class FeeCollectionReportView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, TemplateView):
    template_name = 'finance/fee_collection_report.html'
    permission_required = 'finance.view_finance_report'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        payment_mode = self.request.GET.get('payment_mode')
        
        payments = Payment.objects.filter(
            school=self.request.school,
            status='completed'
        )
        
        if start_date:
            payments = payments.filter(payment_date__gte=start_date)
        if end_date:
            payments = payments.filter(payment_date__lte=end_date)
        if payment_mode:
            payments = payments.filter(payment_mode=payment_mode)
        
        total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
        payment_mode_totals = payments.values('payment_mode').annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        context.update({
            'payments': payments,
            'total_amount': total_amount,
            'payment_mode_totals': payment_mode_totals,
            'start_date': start_date,
            'end_date': end_date,
            'payment_mode': payment_mode,
            'mode_choices': Payment.MODE_CHOICES,
        })
        
        return context
    
    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('format') == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="fee_collection_report.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Date', 'Payment Number', 'Student', 'Amount', 'Payment Mode', 'Reference'])
            
            for payment in context['payments']:
                writer.writerow([
                    payment.payment_date,
                    payment.payment_number,
                    payment.invoice.student.user.get_full_name(),
                    payment.amount,
                    payment.get_payment_mode_display(),
                    payment.reference_number or ''
                ])
            
            return response
        
        return super().render_to_response(context, **response_kwargs)


class OutstandingFeeReportView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, TemplateView):
    template_name = 'finance/outstanding_fee_report.html'
    permission_required = 'finance.view_finance_report'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        academic_year = self.request.GET.get('academic_year')
        class_id = self.request.GET.get('class')
        
        invoices = FeeInvoice.objects.filter(
            school=self.request.school,
            status__in=['issued', 'partial']
        )
        
        if academic_year:
            invoices = invoices.filter(academic_year_id=academic_year)
        if class_id:
            invoices = invoices.filter(student__current_class_id=class_id)
        
        outstanding_invoices = []
        total_outstanding = 0
        
        for invoice in invoices:
            outstanding = invoice.total_amount - invoice.paid_amount
            if outstanding > 0:
                outstanding_invoices.append({
                    'invoice': invoice,
                    'outstanding_amount': outstanding
                })
                total_outstanding += outstanding
        
        context.update({
            'outstanding_invoices': outstanding_invoices,
            'total_outstanding': total_outstanding,
            'academic_years': AcademicYear.objects.filter(school=self.request.school),
            'classes': Class.objects.filter(school=self.request.school, is_active=True),
            'selected_academic_year': academic_year,
            'selected_class': class_id,
        })
        
        return context
    
    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('format') == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="outstanding_fees_report.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Invoice Number', 'Student', 'Class', 'Total Amount', 'Paid Amount', 'Outstanding Amount', 'Due Date'])
            
            for item in context['outstanding_invoices']:
                invoice = item['invoice']
                writer.writerow([
                    invoice.invoice_number,
                    invoice.student.user.get_full_name(),
                    invoice.student.current_class.name,
                    invoice.total_amount,
                    invoice.paid_amount,
                    item['outstanding_amount'],
                    invoice.due_date
                ])
            
            return response
        
        return super().render_to_response(context, **response_kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class GetStudentsForFeeStructureView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            fee_structure_id = data.get('fee_structure_id')
            
            fee_structure = FeeStructure.objects.get(
                id=fee_structure_id,
                school=request.school
            )
            
            students = Student.objects.filter(
                school=request.school,
                is_active=True,
                current_class=fee_structure.class_name
            ).select_related('user')
            
            student_data = []
            for student in students:
                existing_invoice = FeeInvoice.objects.filter(
                    school=request.school,
                    student=student,
                    academic_year=fee_structure.academic_year
                ).exists()
                
                student_data.append({
                    'id': str(student.id),
                    'name': student.user.get_full_name(),
                    'admission_number': student.admission_number,
                    'class': student.current_class.name,
                    'has_invoice': existing_invoice
                })
            
            return JsonResponse({'success': True, 'students': student_data})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class GetInvoiceBalanceView(FinanceAccessRequiredMixin, RoleBasedPermissionMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            invoice_id = data.get('invoice_id')
            
            invoice = FeeInvoice.objects.get(
                id=invoice_id,
                school=request.school
            )
            
            balance = invoice.total_amount - invoice.paid_amount
            
            return JsonResponse({
                'success': True,
                'balance': float(balance),
                'total_amount': float(invoice.total_amount),
                'paid_amount': float(invoice.paid_amount)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
