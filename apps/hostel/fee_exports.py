from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from io import StringIO, BytesIO
import csv
from apps.core.mixins import DirectorRequiredMixin, FinanceAccessRequiredMixin
from .models import HostelFeeStructure
from apps.core.utils import get_user_institution
from utils.utils import render_to_pdf, export_pdf_response
import xlsxwriter

class FeeStructureExportView(FinanceAccessRequiredMixin, View):
    """
    Export Hostel Fee Structure data.
    Supports CSV, PDF, and Excel formats.
    """

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        hostel_id = request.GET.get("hostel")
        room_type = request.GET.get("room_type")
        status = request.GET.get("status")  # active/inactive
        frequency = request.GET.get("frequency")

        # Base queryset
        institution = get_user_institution(request.user)
        qs = HostelFeeStructure.objects.select_related('hostel').filter(
            hostel__institution=institution
        )

        # Apply filters
        if hostel_id:
            qs = qs.filter(hostel_id=hostel_id)

        if room_type:
            qs = qs.filter(room_type=room_type)

        if status:
            if status.lower() == "active":
                qs = qs.filter(is_active=True)
            elif status.lower() == "inactive":
                qs = qs.filter(is_active=False)

        if frequency:
            qs = qs.filter(frequency=frequency)

        # Order by hostel name and effective date
        qs = qs.order_by('hostel__name', '-effective_from', 'room_type')

        # Build filename
        filename_parts = ["hostel_fee_structures"]
        if hostel_id:
            try:
                hostel = qs.first().hostel if qs.exists() else None
                if hostel:
                    filename_parts.append(hostel.name.replace(" ", "_"))
            except:
                pass
        if room_type:
            filename_parts.append(room_type)
        if status:
            filename_parts.append(status)
        if frequency:
            filename_parts.append(frequency)
        
        filename = "_".join(filename_parts).lower()

        # Build data rows
        rows = []
        for fee in qs:
            rows.append({
                "hostel": fee.hostel.name if fee.hostel else "N/A",
                "room_type": fee.get_room_type_display(),
                "amount": float(fee.amount),
                "frequency": fee.get_frequency_display(),
                "effective_from": fee.effective_from.strftime("%Y-%m-%d"),
                "effective_to": fee.effective_to.strftime("%Y-%m-%d") if fee.effective_to else "Ongoing",
                "status": "Active" if fee.is_active else "Inactive",
                "created_at": fee.created_at.strftime("%Y-%m-%d %H:%M"),
            })

        # Get organization info
        organization = get_user_institution(request.user)

        # CSV Export
        if fmt == "csv":
            return self.export_csv(rows, filename, organization)
        
        # PDF Export
        elif fmt == "pdf":
            return self.export_pdf(rows, filename, organization, qs.count())
        
        # Excel Export
        elif fmt == "excel":
            return self.export_excel(rows, filename, organization)
        
        else:
            return HttpResponse("Invalid export format. Supported formats: csv, pdf, excel", status=400)

    def export_csv(self, rows, filename, organization):
        """Export data to CSV format"""
        buffer = StringIO()
        writer = csv.writer(buffer)
        
        # Write header
        writer.writerow([
            'Hostel', 'Room Type', 'Amount (₹)', 'Frequency', 
            'Effective From', 'Effective To', 'Status', 'Created At'
        ])
        
        # Write data rows
        for row in rows:
            writer.writerow([
                row['hostel'],
                row['room_type'],
                row['amount'],
                row['frequency'],
                row['effective_from'],
                row['effective_to'],
                row['status'],
                row['created_at']
            ])
        
        # Add summary row
        writer.writerow([])
        writer.writerow(['Total Fee Structures:', len(rows)])
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_pdf(self, rows, filename, organization, total_count):
        """Export data to PDF format"""
        context = {
            "fee_structures": rows,
            "total_count": total_count,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization.stamp else None,
            "title": "Hostel Fee Structures Export",
            "columns": [
                {'name': 'Hostel', 'width': '20%'},
                {'name': 'Room Type', 'width': '15%'},
                {'name': 'Amount', 'width': '15%'},
                {'name': 'Frequency', 'width': '12%'},
                {'name': 'Effective From', 'width': '12%'},
                {'name': 'Effective To', 'width': '12%'},
                {'name': 'Status', 'width': '8%'},
            ]
        }
        
        pdf_bytes = render_to_pdf("hostel/export/fee_structures_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

    def export_excel(self, rows, filename, organization):
        """Export data to Excel format"""
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Fee Structures')
            
            # Add formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#3b5998',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            money_format = workbook.add_format({'num_format': '₹#,##0.00'})
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            center_format = workbook.add_format({'align': 'center'})
            
            # Write headers
            headers = [
                'Hostel', 'Room Type', 'Amount (₹)', 'Frequency', 
                'Effective From', 'Effective To', 'Status', 'Created At'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Write data
            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data['hostel'])
                worksheet.write(row_idx, 1, row_data['room_type'])
                worksheet.write(row_idx, 2, row_data['amount'], money_format)
                worksheet.write(row_idx, 3, row_data['frequency'])
                worksheet.write(row_idx, 4, row_data['effective_from'], date_format)
                worksheet.write(row_idx, 5, row_data['effective_to'])
                worksheet.write(row_idx, 6, row_data['status'], center_format)
                worksheet.write(row_idx, 7, row_data['created_at'])
            
            # Adjust column widths
            worksheet.set_column('A:A', 25)  # Hostel
            worksheet.set_column('B:B', 15)  # Room Type
            worksheet.set_column('C:C', 15)  # Amount
            worksheet.set_column('D:D', 12)  # Frequency
            worksheet.set_column('E:E', 15)  # Effective From
            worksheet.set_column('F:F', 15)  # Effective To
            worksheet.set_column('G:G', 10)  # Status
            worksheet.set_column('H:H', 20)  # Created At
            
            # Add summary
            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, 'Total Fee Structures:')
            worksheet.write(summary_row, 1, len(rows))
            
            worksheet.write(summary_row + 1, 0, 'Organization:')
            worksheet.write(summary_row + 1, 1, organization.name if organization else 'N/A')
            
            worksheet.write(summary_row + 2, 0, 'Export Date:')
            worksheet.write(summary_row + 2, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))
        
        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response