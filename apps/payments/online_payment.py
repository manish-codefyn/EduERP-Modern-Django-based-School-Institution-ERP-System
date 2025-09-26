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
from django.views.generic import ListView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from apps.core.utils import get_user_institution
from ..models import OnlinePayment

class OnlinePaymentListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = OnlinePayment
    template_name = 'payments/online_payment/online_payment_list.html'
    context_object_name = 'online_payments'
    paginate_by = 20
    permission_required = 'payments.view_onlinepayment'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = OnlinePayment.objects.filter(institution=institution).select_related(
            'payment', 'gateway', 'institution'
        )
        
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        gateway = self.request.GET.get('gateway')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if search:
            queryset = queryset.filter(
                Q(payment__payment_number__icontains=search) |
                Q(gateway_payment_id__icontains=search) |
                Q(gateway_order_id__icontains=search)
            )
        if status:
            queryset = queryset.filter(status=status)
        if gateway:
            queryset = queryset.filter(gateway_id=gateway)
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        stats = OnlinePayment.objects.filter(institution=institution).aggregate(
            total_payments=Count('id'),
            paid_payments=Count('id', filter=Q(status='paid')),
            failed_payments=Count('id', filter=Q(status='failed')),
            refunded_payments=Count('id', filter=Q(status='refunded'))
        )
        
        context.update(stats)
        return context

class OnlinePaymentDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = OnlinePayment
    template_name = 'payments/online_payment/online_payment_detail.html'
    context_object_name = 'online_payment'
    permission_required = 'payments.view_onlinepayment'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return OnlinePayment.objects.filter(institution=institution)

class OnlinePaymentExportView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = OnlinePayment
    context_object_name = "online_payments"
    permission_required = 'payments.view_onlinepayment'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = OnlinePayment.objects.filter(institution=institution).select_related(
            'payment', 'gateway'
        )
        return queryset.order_by('-created_at')

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get("format", "csv").lower()
        queryset = self.get_queryset()

        filename = f"online_payments_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
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
            'Payment ID', 'Gateway', 'Payment Number', 'Amount', 'Currency', 
            'Status', 'Gateway Payment ID', 'Created Date', 'Institution'
        ])

        for payment in queryset:
            writer.writerow([
                str(payment.id),
                payment.gateway.get_gateway_name_display(),
                payment.payment.payment_number,
                str(payment.amount),
                payment.currency,
                payment.get_status_display(),
                payment.gateway_payment_id or '',
                payment.created_at.strftime('%Y-%m-%d %H:%M'),
                organization.name
            ])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, queryset, filename, organization):
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Online Payments")

            header_format = workbook.add_format({
                "bold": True, 
                "bg_color": "#2c3e50", 
                "font_color": "white",
                "border": 1, 
                "align": "center"
            })
            
            headers = [
                'Payment ID', 'Gateway', 'Payment Number', 'Amount', 'Currency', 
                'Status', 'Gateway Payment ID', 'Created Date'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, payment in enumerate(queryset, start=1):
                worksheet.write(row_idx, 0, str(payment.id))
                worksheet.write(row_idx, 1, payment.gateway.get_gateway_name_display())
                worksheet.write(row_idx, 2, payment.payment.payment_number)
                worksheet.write(row_idx, 3, float(payment.amount))
                worksheet.write(row_idx, 4, payment.currency)
                worksheet.write(row_idx, 5, payment.get_status_display())
                worksheet.write(row_idx, 6, payment.gateway_payment_id or '')
                worksheet.write(row_idx, 7, payment.created_at.strftime('%Y-%m-%d %H:%M'))

            worksheet.set_column('A:A', 36)
            worksheet.set_column('B:B', 15)
            worksheet.set_column('C:C', 20)
            worksheet.set_column('D:D', 12)
            worksheet.set_column('E:E', 10)
            worksheet.set_column('F:F', 15)
            worksheet.set_column('G:G', 25)
            worksheet.set_column('H:H', 18)

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
        return response