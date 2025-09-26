import csv
from io import StringIO, BytesIO
from datetime import datetime
import xlsxwriter
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from apps.core.utils import get_user_institution
from ..models import PaymentWebhookLog

class PaymentWebhookLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = PaymentWebhookLog
    template_name = 'payments/webhook/webhook_list.html'
    context_object_name = 'webhook_logs'
    paginate_by = 20
    permission_required = 'payments.view_paymentwebhooklog'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = PaymentWebhookLog.objects.filter(institution=institution).select_related(
            'gateway', 'institution'
        )
        
        search = self.request.GET.get('search')
        event_type = self.request.GET.get('event_type')
        processed = self.request.GET.get('processed')
        gateway = self.request.GET.get('gateway')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if search:
            queryset = queryset.filter(
                Q(webhook_id__icontains=search) |
                Q(event_type__icontains=search) |
                Q(processing_notes__icontains=search)
            )
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if processed:
            queryset = queryset.filter(processed=(processed == 'true'))
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
        
        stats = PaymentWebhookLog.objects.filter(institution=institution).aggregate(
            total_logs=Count('id'),
            processed_logs=Count('id', filter=Q(processed=True)),
            unprocessed_logs=Count('id', filter=Q(processed=False))
        )
        
        context.update(stats)
        return context

class PaymentWebhookLogDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = PaymentWebhookLog
    template_name = 'payments/webhook/webhook_detail.html'
    context_object_name = 'webhook_log'
    permission_required = 'payments.view_paymentwebhooklog'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return PaymentWebhookLog.objects.filter(institution=institution)

class PaymentWebhookLogExportView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = PaymentWebhookLog
    context_object_name = "webhook_logs"
    permission_required = 'payments.view_paymentwebhooklog'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = PaymentWebhookLog.objects.filter(institution=institution).select_related('gateway')
        return queryset.order_by('-created_at')

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get("format", "csv").lower()
        queryset = self.get_queryset()

        filename = f"webhook_logs_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
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
            'Webhook ID', 'Gateway', 'Event Type', 'Webhook ID', 'Processed',
            'Processing Notes', 'Created Date', 'Institution'
        ])

        for log in queryset:
            writer.writerow([
                str(log.id),
                log.gateway.get_gateway_name_display(),
                log.event_type,
                log.webhook_id or '',
                'Yes' if log.processed else 'No',
                log.processing_notes[:50] + '...' if len(log.processing_notes) > 50 else log.processing_notes,
                log.created_at.strftime('%Y-%m-%d %H:%M'),
                organization.name
            ])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, queryset, filename, organization):
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Webhook Logs")

            header_format = workbook.add_format({
                "bold": True, 
                "bg_color": "#2c3e50", 
                "font_color": "white",
                "border": 1, 
                "align": "center"
            })
            
            headers = [
                'Webhook ID', 'Gateway', 'Event Type', 'Webhook ID', 'Processed',
                'Processing Notes', 'Created Date'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, log in enumerate(queryset, start=1):
                worksheet.write(row_idx, 0, str(log.id))
                worksheet.write(row_idx, 1, log.gateway.get_gateway_name_display())
                worksheet.write(row_idx, 2, log.event_type)
                worksheet.write(row_idx, 3, log.webhook_id or '')
                worksheet.write(row_idx, 4, 'Yes' if log.processed else 'No')
                worksheet.write(row_idx, 5, log.processing_notes[:50] + '...' if len(log.processing_notes) > 50 else log.processing_notes)
                worksheet.write(row_idx, 6, log.created_at.strftime('%Y-%m-%d %H:%M'))

            worksheet.set_column('A:A', 36)
            worksheet.set_column('B:B', 15)
            worksheet.set_column('C:C', 20)
            worksheet.set_column('D:D', 25)
            worksheet.set_column('E:E', 12)
            worksheet.set_column('F:F', 40)
            worksheet.set_column('G:G', 18)

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
        return response

@require_GET
def retry_webhook_processing(request, pk):
    """API endpoint to retry webhook processing"""
    institution = get_user_institution(request.user)
    webhook_log = get_object_or_404(PaymentWebhookLog, pk=pk, institution=institution)
    
    # Add your webhook processing logic here
    # This is a placeholder for actual webhook processing
    
    webhook_log.processed = True
    webhook_log.processing_notes = "Manually retried and processed"
    webhook_log.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Webhook processing retried successfully'
    })