from io import StringIO, BytesIO
import csv
import xlsxwriter
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import ListView,DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from utils.utils import render_to_pdf, export_pdf_response  
from apps.core.utils import get_user_institution
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import StaffManagementRequiredMixin
from .models import StockTransaction


class StockTransactionExportView(StaffManagementRequiredMixin, ListView):
    model = StockTransaction
    context_object_name = "transactions"

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return StockTransaction.objects.select_related('item', 'performed_by').filter(institution=institution).order_by('-transaction_date')

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get("format", "csv").lower()
        queryset = self.get_queryset()
        filename = f"stock_transactions_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        organization = get_user_institution(request.user)

        if format_type == "csv":
            return self.export_csv(queryset, filename, organization)
        elif format_type == "excel":
            return self.export_excel(queryset, filename, organization)
        elif format_type == "pdf":
            return self.export_pdf(queryset, filename, organization)
        return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, queryset, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        writer.writerow(['Item', 'Type', 'Quantity', 'Previous Qty', 'New Qty', 'Reference', 'Notes', 'Performed By', 'Date'])

        for txn in queryset:
            writer.writerow([
                txn.item.name,
                txn.get_transaction_type_display(),
                txn.quantity,
                txn.previous_quantity,
                txn.new_quantity,
                txn.reference or '-',
                txn.notes or '-',
                txn.performed_by.get_full_name(),
                txn.transaction_date.strftime('%Y-%m-%d %H:%M')
            ])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, queryset, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Transactions")
            header_format = workbook.add_format({
                "bold": True, "bg_color": "#2c3e50", "font_color": "white",
                "border": 1, "align": "center", "valign": "vcenter"
            })

            headers = ['Item', 'Type', 'Quantity', 'Previous Qty', 'New Qty', 'Reference', 'Notes', 'Performed By', 'Date']
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, txn in enumerate(queryset, start=1):
                worksheet.write(row_idx, 0, txn.item.name)
                worksheet.write(row_idx, 1, txn.get_transaction_type_display())
                worksheet.write(row_idx, 2, txn.quantity)
                worksheet.write(row_idx, 3, txn.previous_quantity)
                worksheet.write(row_idx, 4, txn.new_quantity)
                worksheet.write(row_idx, 5, txn.reference or '-')
                worksheet.write(row_idx, 6, txn.notes or '-')
                worksheet.write(row_idx, 7, txn.performed_by.get_full_name())
                worksheet.write(row_idx, 8, txn.transaction_date.strftime('%Y-%m-%d %H:%M'))

            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:B', 15)
            worksheet.set_column('C:E', 12)
            worksheet.set_column('F:G', 20)
            worksheet.set_column('H:H', 25)
            worksheet.set_column('I:I', 20)

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, queryset, filename, organization):
        context = {
            "transactions": queryset,
            "total_count": queryset.count(),
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Stock Transactions Export",
        }
        pdf_bytes = render_to_pdf("inventory/export/stock_transaction_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)


class StockTransactionDetailExportView( StaffManagementRequiredMixin, DetailView):
    model = StockTransaction
    pk_url_kwarg = 'pk'

    def get(self, request, *args, **kwargs):
        transaction = self.get_object()
        format_type = request.GET.get("format", "pdf").lower()
        organization = get_user_institution(request.user)
        filename = f"stock_transaction_{transaction.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        if format_type == "csv":
            return self.export_csv(transaction, filename)
        elif format_type == "excel":
            return self.export_excel(transaction, filename)
        elif format_type == "pdf":
            return self.export_pdf(transaction, filename, organization)
        return HttpResponse("Invalid format", status=400)

    def export_csv(self, transaction, filename):
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['Field', 'Value'])
        writer.writerow(['Item', transaction.item.name])
        writer.writerow(['Transaction Type', transaction.get_transaction_type_display()])
        writer.writerow(['Quantity', transaction.quantity])
        writer.writerow(['Previous Quantity', transaction.previous_quantity])
        writer.writerow(['New Quantity', transaction.new_quantity])
        writer.writerow(['Reference', transaction.reference or '-'])
        writer.writerow(['Notes', transaction.notes or '-'])
        writer.writerow(['Performed By', transaction.performed_by.get_full_name()])
        writer.writerow(['Date', transaction.transaction_date.strftime('%Y-%m-%d %H:%M')])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, transaction, filename):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Transaction")
            header_format = workbook.add_format({"bold": True, "bg_color": "#2c3e50", "font_color": "white", "border": 1})
            
            data = [
                ('Item', transaction.item.name),
                ('Transaction Type', transaction.get_transaction_type_display()),
                ('Quantity', transaction.quantity),
                ('Previous Quantity', transaction.previous_quantity),
                ('New Quantity', transaction.new_quantity),
                ('Reference', transaction.reference or '-'),
                ('Notes', transaction.notes or '-'),
                ('Performed By', transaction.performed_by.get_full_name()),
                ('Date', transaction.transaction_date.strftime('%Y-%m-%d %H:%M')),
            ]

            for row_idx, (field, value) in enumerate(data):
                worksheet.write(row_idx, 0, field, header_format)
                worksheet.write(row_idx, 1, value)

            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:B', 40)

        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, transaction, filename, organization):
        context = {
            "transaction": transaction,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Stock Transaction Detail",
        }
        pdf_bytes = render_to_pdf("inventory/export/stock_transaction_detail_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)