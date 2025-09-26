import csv
from io import StringIO, BytesIO
from datetime import datetime
import xlsxwriter
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.views.decorators.http import require_GET, require_POST
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from apps.core.mixins import StaffManagementRequiredMixin
from apps.core.utils import get_user_institution
from ..models import PaymentGateway
from ..forms import PaymentGatewayForm

class PaymentGatewayListView(LoginRequiredMixin, StaffManagementRequiredMixin, ListView):
    model = PaymentGateway
    template_name = 'payments/gateway/gateway_list.html'
    context_object_name = 'gateways'
    paginate_by = 20
    permission_required = 'payments.view_paymentgateway'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = PaymentGateway.objects.filter(institution=institution).select_related('institution')
        
        search = self.request.GET.get('search')
        gateway_name = self.request.GET.get('gateway_name')
        status = self.request.GET.get('status')
        
        if search:
            queryset = queryset.filter(
                Q(api_key__icontains=search) |
                Q(merchant_id__icontains=search)
            )
        if gateway_name:
            queryset = queryset.filter(gateway_name=gateway_name)
        if status:
            if status == 'active':
                queryset = queryset.filter(is_active=True)
            elif status == 'inactive':
                queryset = queryset.filter(is_active=False)
        
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        stats = PaymentGateway.objects.filter(institution=institution).aggregate(
            total_gateways=Count('id'),
            active_gateways=Count('id', filter=Q(is_active=True)),
            test_gateways=Count('id', filter=Q(test_mode=True))
        )
        
        context.update(stats)
        context['gateway_choices'] = PaymentGateway.GATEWAY_CHOICES
        return context

class PaymentGatewayCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = PaymentGateway
    form_class = PaymentGatewayForm
    template_name = 'payments/gateway/gateway_form.html'
    permission_required = 'payments.add_paymentgateway'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, "Payment gateway created successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('payments:gateway_detail', kwargs={'pk': self.object.pk})

class PaymentGatewayUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = PaymentGateway
    form_class = PaymentGatewayForm
    template_name = 'payments/gateway/gateway_form.html'
    permission_required = 'payments.change_paymentgateway'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return PaymentGateway.objects.filter(institution=institution)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Payment gateway updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('payments:gateway_detail', kwargs={'pk': self.object.pk})

class PaymentGatewayDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = PaymentGateway
    template_name = 'payments/gateway/gateway_detail.html'
    context_object_name = 'gateway'
    permission_required = 'payments.view_paymentgateway'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return PaymentGateway.objects.filter(institution=institution)

class PaymentGatewayDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = PaymentGateway
    template_name = 'payments/gateway/gateway_confirm_delete.html'
    success_url = reverse_lazy('payments:gateway_list')
    permission_required = 'payments.delete_paymentgateway'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return PaymentGateway.objects.filter(institution=institution)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        gateway_name = self.object.get_gateway_name_display()
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Payment gateway "{gateway_name}" has been deleted successfully.')
        return response

class PaymentGatewayExportView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = PaymentGateway
    context_object_name = "gateways"
    permission_required = 'payments.view_paymentgateway'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return PaymentGateway.objects.filter(institution=institution).select_related('institution')

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get("format", "csv").lower()
        queryset = self.get_queryset()

        filename = f"payment_gateways_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
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
            'Gateway ID', 'Gateway Name', 'Status', 'Mode', 'API Key', 
            'Merchant ID', 'Created Date', 'Updated Date', 'Institution'
        ])

        for gateway in queryset:
            writer.writerow([
                str(gateway.id),
                gateway.get_gateway_name_display(),
                'Active' if gateway.is_active else 'Inactive',
                'Test' if gateway.test_mode else 'Live',
                gateway.api_key[:10] + '...' if gateway.api_key else '',
                gateway.merchant_id or '',
                gateway.created_at.strftime('%Y-%m-%d %H:%M'),
                gateway.updated_at.strftime('%Y-%m-%d %H:%M'),
                organization.name
            ])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, queryset, filename, organization):
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Payment Gateways")

            header_format = workbook.add_format({
                "bold": True, 
                "bg_color": "#2c3e50", 
                "font_color": "white",
                "border": 1, 
                "align": "center"
            })
            
            headers = [
                'Gateway ID', 'Gateway Name', 'Status', 'Mode', 'API Key', 
                'Merchant ID', 'Created Date', 'Updated Date'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, gateway in enumerate(queryset, start=1):
                worksheet.write(row_idx, 0, str(gateway.id))
                worksheet.write(row_idx, 1, gateway.get_gateway_name_display())
                worksheet.write(row_idx, 2, 'Active' if gateway.is_active else 'Inactive')
                worksheet.write(row_idx, 3, 'Test' if gateway.test_mode else 'Live')
                worksheet.write(row_idx, 4, gateway.api_key[:10] + '...' if gateway.api_key else '')
                worksheet.write(row_idx, 5, gateway.merchant_id or '')
                worksheet.write(row_idx, 6, gateway.created_at.strftime('%Y-%m-%d %H:%M'))
                worksheet.write(row_idx, 7, gateway.updated_at.strftime('%Y-%m-%d %H:%M'))

            worksheet.set_column('A:A', 36)
            worksheet.set_column('B:B', 20)
            worksheet.set_column('C:D', 15)
            worksheet.set_column('E:E', 25)
            worksheet.set_column('F:F', 20)
            worksheet.set_column('G:H', 18)

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
        return response