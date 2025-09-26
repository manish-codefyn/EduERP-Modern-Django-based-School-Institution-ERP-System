from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import HttpResponse
from django.utils import timezone
from io import StringIO, BytesIO
import csv
import xlsxwriter

from apps.core.mixins import FinanceAccessRequiredMixin
from apps.core.utils import get_user_institution
from utils.utils import render_to_pdf, export_pdf_response
from .models import Hostel


class HostelExportView(FinanceAccessRequiredMixin, View):
    """
    Export Hostel data in CSV, PDF, Excel formats
    """

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        gender = request.GET.get("gender")
        status = request.GET.get("status")  # active/inactive

        institution = get_user_institution(request.user)
        qs = Hostel.objects.filter(institution=institution)

        if gender:
            qs = qs.filter(gender_type=gender)

        if status:
            if status.lower() == "active":
                qs = qs.filter(is_active=True)
            elif status.lower() == "inactive":
                qs = qs.filter(is_active=False)

        qs = qs.order_by("name")

        # Build filename
        filename_parts = ["hostels"]
        if gender:
            filename_parts.append(gender)
        if status:
            filename_parts.append(status)
        filename = "_".join(filename_parts).lower()

        # Prepare rows
        rows = []
        for hostel in qs:
            rows.append({
                "name": hostel.name,
                "code": hostel.code or "-",
                "gender_type": hostel.get_gender_type_display(),
                "capacity": hostel.capacity,
                "current_occupancy": hostel.current_occupancy,
                "available_beds": hostel.available_beds(),
                "warden": hostel.warden.user.get_full_name if hostel.warden else "N/A",
                "assistant_warden": hostel.assistant_warden.user.get_full_name if hostel.assistant_warden else "N/A",
                "contact_number": hostel.contact_number,
                "email": hostel.email,
                "security_deposit": float(hostel.security_deposit),
                "monthly_charges": float(hostel.monthly_charges),
                "status": "Active" if hostel.is_active else "Inactive",
                "created_at": hostel.created_at.strftime("%Y-%m-%d %H:%M"),
            })

        organization = institution

        if fmt == "csv":
            return self.export_csv(rows, filename, organization)

        elif fmt == "pdf":
            return self.export_pdf(rows, filename, organization, qs.count())

        elif fmt == "excel":
            return self.export_excel(rows, filename, organization)

        return HttpResponse("Invalid format. Use csv, pdf, excel.", status=400)

    def export_csv(self, rows, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        writer.writerow([
            "Name", "Code", "Gender", "Capacity", "Occupied", "Available Beds",
            "Warden", "Assistant Warden", "Contact", "Email", 
            "Security Deposit (₹)", "Monthly Charges (₹)", "Status", "Created At"
        ])

        for row in rows:
            writer.writerow([
                row['name'], row['code'], row['gender_type'], row['capacity'],
                row['current_occupancy'], row['available_beds'],
                row['warden'], row['assistant_warden'], row['contact_number'],
                row['email'], row['security_deposit'], row['monthly_charges'],
                row['status'], row['created_at']
            ])

        writer.writerow([])
        writer.writerow(["Total Hostels:", len(rows)])
        writer.writerow(["Organization:", organization.name if organization else "N/A"])
        writer.writerow(["Export Date:", timezone.now().strftime("%Y-%m-%d %H:%M")])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_pdf(self, rows, filename, organization, total_count):
        context = {
            "hostels": rows,
            "total_count": total_count,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Hostel Export",
            "columns": [
                {"name": "Name", "width": "15%"},
                {"name": "Code", "width": "10%"},
                {"name": "Gender", "width": "10%"},
                {"name": "Capacity", "width": "8%"},
                {"name": "Occupied", "width": "8%"},
                {"name": "Available Beds", "width": "10%"},
                {"name": "Warden", "width": "12%"},
                {"name": "Assistant", "width": "12%"},
                {"name": "Status", "width": "8%"},
            ]
        }

        pdf_bytes = render_to_pdf("hostel/export/hostels_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

    def export_excel(self, rows, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            ws = workbook.add_worksheet("Hostels")

            header_fmt = workbook.add_format({"bold": True, "bg_color": "#3b5998", "font_color": "white"})
            money_fmt = workbook.add_format({"num_format": "₹#,##0.00"})

            headers = [
                "Name", "Code", "Gender", "Capacity", "Occupied", "Available Beds",
                "Warden", "Assistant Warden", "Contact", "Email",
                "Security Deposit (₹)", "Monthly Charges (₹)", "Status", "Created At"
            ]

            for col, h in enumerate(headers):
                ws.write(0, col, h, header_fmt)

            for i, r in enumerate(rows, start=1):
                ws.write(i, 0, r['name'])
                ws.write(i, 1, r['code'])
                ws.write(i, 2, r['gender_type'])
                ws.write(i, 3, r['capacity'])
                ws.write(i, 4, r['current_occupancy'])
                ws.write(i, 5, r['available_beds'])
                ws.write(i, 6, r['warden'])
                ws.write(i, 7, r['assistant_warden'])
                ws.write(i, 8, r['contact_number'])
                ws.write(i, 9, r['email'])
                ws.write(i, 10, r['security_deposit'], money_fmt)
                ws.write(i, 11, r['monthly_charges'], money_fmt)
                ws.write(i, 12, r['status'])
                ws.write(i, 13, r['created_at'])

            ws.set_column("A:N", 20)

            summary_row = len(rows) + 2
            ws.write(summary_row, 0, "Total Hostels:")
            ws.write(summary_row, 1, len(rows))
            ws.write(summary_row + 1, 0, "Organization:")
            ws.write(summary_row + 1, 1, organization.name if organization else "N/A")
            ws.write(summary_row + 2, 0, "Export Date:")
            ws.write(summary_row + 2, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response
