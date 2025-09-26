import csv
from io import StringIO, BytesIO
from datetime import datetime
import xlsxwriter
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from apps.core.utils import get_user_institution
from ..models import Refund, OnlinePayment
from ..forms import RefundForm

class RefundListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Refund
    template_name = 'payments/refund/refund_list.html'
    context_object_name = 'refunds'
    paginate_by = 20
    permission_required = 'payments.view_refund'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = Refund.objects.filter(institution=institution).select_related(
            'online_payment', 'created_by', 'institution'
        )
        
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if search:
            queryset = queryset.filter(
                Q(online_payment__payment__payment_number__icontains=search) |
                Q(gateway_refund_id__icontains=search) |
                Q(reason__icontains=search)
            )
        if status:
            queryset = queryset.filter(status=status)
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        stats = Refund.objects.filter(institution=institution).aggregate(
            total_refunds=Count('id'),
            pending_refunds=Count('id', filter=Q(status='pending')),
            processed_refunds=Count('id', filter=Q(status='processed')),
            failed_refunds=Count('id', filter=Q(status='failed'))
        )
        
        context.update(stats)
        return context

class RefundCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Refund
    form_class = RefundForm
    template_name = 'payments/refund/refund_form.html'
    permission_required = 'payments.add_refund'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        form.instance.created_by = self.request.user
        messages.success(self.request, "Refund created successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('payments:refund_detail', kwargs={'pk': self.object.pk})

class RefundUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Refund
    form_class = RefundForm
    template_name = 'payments/refund/refund_form.html'
    permission_required = 'payments.change_refund'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Refund.objects.filter(institution=institution)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Refund updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('payments:refund_detail', kwargs={'pk': self.object.pk})

class RefundDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Refund
    template_name = 'payments/refund/refund_detail.html'
    context_object_name = 'refund'
    permission_required = 'payments.view_refund'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Refund.objects.filter(institution=institution)

class RefundDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Refund
    template_name = 'payments/refund/refund_confirm_delete.html'
    success_url = reverse_lazy('payments:refund_list')
    permission_required = 'payments.delete_refund'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Refund.objects.filter(institution=institution)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        refund_amount = self.object.refund_amount
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Refund of {refund_amount} has been deleted successfully.')
        return response

class RefundExportView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Refund
    context_object_name = "refunds"
    permission_required = 'payments.view_refund'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = Refund.objects.filter(institution=institution).select_related(
            'online_payment', 'created_by'
        )
        return queryset.order_by('-created_at')

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get("format", "csv").lower()
        queryset = self.get_queryset()

        filename = f"refunds_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        organization = get_user_institution(request.user)

        if format_type == "csv":
            return self.export_csv(queryset, filename, organization)
        elif format_type == "excel":
            return self.export_excel(queryset, filename, organization)
        return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, queryset, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        writer.writerow([
            'Refund ID', 'Payment Number', 'Refund Amount', 'Currency', 'Status',
            'Gateway Refund ID', 'Reason', 'Created By', 'Created Date', 'Institution'
        ])

        for refund in queryset:
            writer.writerow([
                str(refund.id),
                refund.online_payment.payment.payment_number,
                str(refund.refund_amount),
                refund.online_payment.currency,
                refund.get_status_display(),
                refund.gateway_refund_id or '',
                refund.reason[:50] + '...' if len(refund.reason) > 50 else refund.reason,
                refund.created_by.get_full_name() or refund.created_by.username,
                refund.created_at.strftime('%Y-%m-%d %H:%M'),
                organization.name
            ])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, queryset, filename, organization):
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Refunds")

            header_format = workbook.add_format({
                "bold": True, 
                "bg_color": "#2c3e50", 
                "font_color": "white",
                "border": 1, 
                "align": "center"
            })
            
            headers = [
                'Refund ID', 'Payment Number', 'Refund Amount', 'Currency', 'Status',
                'Gateway Refund ID', 'Reason', 'Created By', 'Created Date'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, refund in enumerate(queryset, start=1):
                worksheet.write(row_idx, 0, str(refund.id))
                worksheet.write(row_idx, 1, refund.online_payment.payment.payment_number)
                worksheet.write(row_idx, 2, float(refund.refund_amount))
                worksheet.write(row_idx, 3, refund.online_payment.currency)
                worksheet.write(row_idx, 4, refund.get_status_display())
                worksheet.write(row_idx, 5, refund.gateway_refund_id or '')
                worksheet.write(row_idx, 6, refund.reason[:50] + '...' if len(refund.reason) > 50 else refund.reason)
                worksheet.write(row_idx, 7, refund.created_by.get_full_name() or refund.created_by.username)
                worksheet.write(row_idx, 8, refund.created_at.strftime('%Y-%m-%d %H:%M'))

            worksheet.set_column('A:A', 36)
            worksheet.set_column('B:B', 20)
            worksheet.set_column('C:C', 15)
            worksheet.set_column('D:D', 10)
            worksheet.set_column('E:E', 15)
            worksheet.set_column('F:F', 25)
            worksheet.set_column('G:G', 40)
            worksheet.set_column('H:H', 20)
            worksheet.set_column('I:I', 18)

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
        return response