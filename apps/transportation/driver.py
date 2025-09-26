import csv
from io import StringIO, BytesIO
from datetime import datetime
import xlsxwriter
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import StaffManagementRequiredMixin
from .models import Driver
from .forms import DriverForm, DriverFilterForm
from apps.core.utils import get_user_institution
from utils.utils import render_to_pdf, export_pdf_response

# ----------------- DRIVER CRUD -----------------

class DriverListView( StaffManagementRequiredMixin, ListView):
    model = Driver
    template_name = 'transport/driver/driver_list.html'
    context_object_name = 'drivers'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = Driver.objects.filter(institution=institution)

        search = self.request.GET.get('search')
        status = self.request.GET.get('status')

        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(license_number__icontains=search)
            )

        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        context['total_drivers'] = queryset.count()
        context['active_drivers'] = queryset.filter(is_active=True).count()
        context['inactive_drivers'] = queryset.filter(is_active=False).count()
        context['filter_form'] = DriverFilterForm(self.request.GET)
        return context

class DriverCreateView( StaffManagementRequiredMixin, CreateView):
    model = Driver
    form_class = DriverForm
    template_name = 'transport/driver/driver_form.html'

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, "Driver created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('transport:driver_list')

class DriverUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = Driver
    form_class = DriverForm
    template_name = 'transport/driver/driver_form.html'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Driver.objects.filter(institution=institution)

    def form_valid(self, form):
        messages.success(self.request, "Driver updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('transport:driver_list')

class DriverDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = Driver
    template_name = 'transport/driver/driver_confirm_delete.html'
    context_object_name = 'driver'
    success_url = reverse_lazy('transport:driver_list')

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Driver.objects.filter(institution=institution)

class DriverDetailView( StaffManagementRequiredMixin, DetailView):
    model = Driver
    template_name = 'transport/driver/driver_detail.html'
    context_object_name = 'driver'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Driver.objects.filter(institution=institution)


# ----------------- DRIVER EXPORT -----------------

class DriverExportView( StaffManagementRequiredMixin, ListView):
    model = Driver

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Driver.objects.filter(institution=institution)

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get("format", "csv").lower()
        queryset = self.get_queryset()

        # Apply filters
        form = DriverFilterForm(request.GET)
        if form.is_valid():
            status = form.cleaned_data.get('status')
            if status == 'active':
                queryset = queryset.filter(is_active=True)
            elif status == 'inactive':
                queryset = queryset.filter(is_active=False)
            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(user__first_name__icontains=search) |
                    Q(user__last_name__icontains=search) |
                    Q(license_number__icontains=search)
                )

        filename = f"driver_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        rows = []
        for driver in queryset:
            rows.append({
                "name": driver.user.get_full_name(),
                "license_number": driver.license_number,
                "license_type": driver.license_type,
                "license_expiry": driver.license_expiry.strftime("%Y-%m-%d"),
                "experience": driver.experience,
                "contact": driver.emergency_contact,
                "status": "Active" if driver.is_active else "Inactive",
            })

        organization = get_user_institution(request.user)

        if format_type == "csv":
            return self.export_csv(rows, filename, organization)
        elif format_type == "excel":
            return self.export_excel(rows, filename, organization)
        elif format_type == "pdf":
            return self.export_pdf(rows, filename, organization, queryset.count())
        return HttpResponse("Invalid format specified", status=400)

    # --- CSV ---
    def export_csv(self, rows, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Name", "License Number", "License Type", "Expiry Date", "Experience", "Emergency Contact", "Status"])
        for row in rows:
            writer.writerow([row['name'], row['license_number'], row['license_type'], row['license_expiry'], row['experience'], row['contact'], row['status']])
        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    # --- Excel ---
    def export_excel(self, rows, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            ws = workbook.add_worksheet("Drivers")
            headers = ["Name", "License Number", "License Type", "Expiry Date", "Experience", "Emergency Contact", "Status"]
            for col, header in enumerate(headers):
                ws.write(0, col, header)
            for row_idx, row in enumerate(rows, start=1):
                ws.write(row_idx, 0, row['name'])
                ws.write(row_idx, 1, row['license_number'])
                ws.write(row_idx, 2, row['license_type'])
                ws.write(row_idx, 3, row['license_expiry'])
                ws.write(row_idx, 4, row['experience'])
                ws.write(row_idx, 5, row['contact'])
                ws.write(row_idx, 6, row['status'])
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response

    # --- PDF ---
    def export_pdf(self, rows, filename, organization, total_count):
        context = {
            "records": rows,
            "total_count": total_count,
            "active_count": len([r for r in rows if r['status'] == 'Active']),
            "export_date": timezone.now(),
            "organization": organization,
            "title": "Driver Export",
            "columns": [
                {"name": "Name", "width": "20%"},
                {"name": "License Number", "width": "15%"},
                {"name": "License Type", "width": "10%"},
                {"name": "Expiry Date", "width": "12%"},
                {"name": "Experience", "width": "10%"},
                {"name": "Contact", "width": "15%"},
                {"name": "Status", "width": "10%"},
            ]
        }
        pdf_bytes = render_to_pdf("transport/driver/driver_export_pdf.html", context)
        return export_pdf_response(pdf_bytes, f"{filename}.pdf")
