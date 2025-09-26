

# apps/transportation/views.py
import csv
from io import StringIO, BytesIO
from datetime import datetime
import xlsxwriter
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Count, Q


from utils.utils import render_to_pdf, export_pdf_response  # your PDF utils

from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import StaffManagementRequiredMixin
from .models import StudentTransport
from .forms import StudentTransportForm,StudentTransportFilterForm
from apps.core.utils import get_user_institution



# List View

class StudentTransportListView( StaffManagementRequiredMixin, ListView):
    model = StudentTransport
    template_name = 'transport/student_transport_list.html'
    context_object_name = 'student_transports'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = StudentTransport.objects.filter(institution=institution)

        # Optional filters (search, active status, etc.)
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')

        if search:
            queryset = queryset.filter(
                Q(student__name__icontains=search) |
                Q(transport_assignment__name__icontains=search)
            )

        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)

        stats = StudentTransport.objects.filter(institution=institution).aggregate(
            total_assignments=Count('id'),
            active_assignments=Count('id', filter=Q(is_active=True)),
            inactive_assignments=Count('id', filter=Q(is_active=False)),
        )

        # Upcoming expiries (assignments ending in next 30 days)
        upcoming_end = StudentTransport.objects.filter(
            institution=institution,
            end_date__isnull=False,
            end_date__gte=timezone.now().date(),
            end_date__lte=timezone.now().date() + timezone.timedelta(days=30)
        ).count()

        context.update({
            "total_assignments": stats["total_assignments"],
            "active_assignments": stats["active_assignments"],
            "inactive_assignments": stats["inactive_assignments"],
            "upcoming_end": upcoming_end,
        })
        return context

# Create View
class StudentTransportCreateView( StaffManagementRequiredMixin, CreateView):
    model = StudentTransport
    form_class = StudentTransportForm
    template_name = 'transport/student_transport_form.html'

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, "Student transport assignment created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('transport:student_transport_list')

# Update View
class StudentTransportUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = StudentTransport
    form_class = StudentTransportForm
    template_name = 'transport/student_transport_form.html'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return StudentTransport.objects.filter(institution=institution)

    def form_valid(self, form):
        messages.success(self.request, "Student transport assignment updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('transport:student_transport_list')

# Delete View
class StudentTransportDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = StudentTransport
    template_name = 'transport/student_transport_confirm_delete.html'
    context_object_name = 'student_transport'
    success_url = reverse_lazy('transport:student_transport_list')

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return StudentTransport.objects.filter(institution=institution)


class StudentTransportExportView( StaffManagementRequiredMixin, ListView):
    model = StudentTransport
    context_object_name = "student_transports"

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return StudentTransport.objects.select_related(
            "student", "transport_assignment", "pickup_stop", "drop_stop"
        ).filter(institution=institution)

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get("format", "csv").lower()
        queryset = self.get_queryset()

        # Optional filters
        form = StudentTransportFilterForm(request.GET, request=request)
        if form.is_valid():
            active_status = form.cleaned_data.get("status")
            if active_status == "active":
                queryset = queryset.filter(is_active=True)
            elif active_status == "inactive":
                queryset = queryset.filter(is_active=False)

        filename = f"student_transport_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        rows = []
        for st in queryset:
            rows.append({
                "student": str(st.student),
                "assignment": str(st.transport_assignment),
                "pickup_stop": str(st.pickup_stop),
                "drop_stop": str(st.drop_stop),
                "start_date": st.start_date.strftime("%Y-%m-%d"),
                "end_date": st.end_date.strftime("%Y-%m-%d") if st.end_date else "N/A",
                "status": "Active" if st.is_active else "Inactive",
            })

        organization = get_user_institution(request.user)

        if format_type == "csv":
            return self.export_csv(rows, filename, organization)
        elif format_type == "excel":
            return self.export_excel(rows, filename, organization)
        elif format_type == "pdf":
            return self.export_pdf(rows, filename, organization, queryset.count())
        return HttpResponse("Invalid format specified", status=400)

    # ---------- CSV ----------
    def export_csv(self, rows, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        writer.writerow([
            "Student", "Transport Assignment", "Pickup Stop", "Drop Stop",
            "Start Date", "End Date", "Status"
        ])

        for row in rows:
            writer.writerow([
                row["student"],
                row["assignment"],
                row["pickup_stop"],
                row["drop_stop"],
                row["start_date"],
                row["end_date"],
                row["status"],
            ])

        writer.writerow([])
        writer.writerow(["Total Records:", len(rows)])
        active_count = len([r for r in rows if r["status"] == "Active"])
        writer.writerow(["Active Records:", active_count])
        writer.writerow(["Organization:", organization.name if organization else "N/A"])
        writer.writerow(["Export Date:", timezone.now().strftime("%Y-%m-%d %H:%M")])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return response

    # ---------- Excel ----------
    def export_excel(self, rows, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Student Transport")

            header_format = workbook.add_format({
                "bold": True, "bg_color": "#2c3e50", "font_color": "white",
                "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True
            })

            headers = [
                "Student", "Transport Assignment", "Pickup Stop", "Drop Stop",
                "Start Date", "End Date", "Status"
            ]

            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data["student"])
                worksheet.write(row_idx, 1, row_data["assignment"])
                worksheet.write(row_idx, 2, row_data["pickup_stop"])
                worksheet.write(row_idx, 3, row_data["drop_stop"])
                worksheet.write(row_idx, 4, row_data["start_date"])
                worksheet.write(row_idx, 5, row_data["end_date"])
                worksheet.write(row_idx, 6, row_data["status"])

            worksheet.set_column("A:B", 25)
            worksheet.set_column("C:D", 20)
            worksheet.set_column("E:F", 15)
            worksheet.set_column("G:G", 12)

            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, "Total Records:")
            worksheet.write(summary_row, 1, len(rows))

            active_count = len([r for r in rows if r["status"] == "Active"])
            worksheet.write(summary_row + 1, 0, "Active Records:")
            worksheet.write(summary_row + 1, 1, active_count)

            worksheet.write(summary_row + 3, 0, "Organization:")
            worksheet.write(summary_row + 3, 1, organization.name if organization else "N/A")
            worksheet.write(summary_row + 4, 0, "Export Date:")
            worksheet.write(summary_row + 4, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
        return response

    # ---------- PDF ----------
    def export_pdf(self, rows, filename, organization, total_count):
        active_count = len([r for r in rows if r["status"] == "Active"])
        context = {
            "records": rows,
            "total_count": total_count,
            "active_count": active_count,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Student Transport Export",
            "columns": [
                {"name": "Student", "width": "26%"},
                {"name": "Assignment", "width": "20%"},
                {"name": "Pickup", "width": "15%"},
                {"name": "Drop", "width": "15%"},
                {"name": "Start Date", "width": "8%"},
                {"name": "End Date", "width": "8%"},
                {"name": "Status", "width": "8%"},
            ],
        }
        pdf_bytes = render_to_pdf("transport/export/student_transport_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)
