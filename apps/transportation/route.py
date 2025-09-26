# apps/transport/views/route_views.py
import csv
from io import StringIO, BytesIO
from datetime import datetime
import xlsxwriter
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin

from utils.utils import render_to_pdf, export_pdf_response
from apps.core.mixins import StaffManagementRequiredMixin
from apps.core.utils import get_user_institution
from .models import Route
from .forms import RouteForm, RouteFilterForm

class RouteListView( StaffManagementRequiredMixin, ListView):
    model = Route
    template_name = 'transport/route/route_list.html'
    context_object_name = 'routes'
    paginate_by = 25

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = Route.objects.filter(institution=institution).prefetch_related('stops').order_by('name')

        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(start_point__icontains=search) |
                Q(end_point__icontains=search)
            )

        # Status filter
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Statistics
        routes = Route.objects.filter(institution=institution)
        stats = routes.aggregate(
            total_routes=Count('id'),
            active_routes=Count('id', filter=Q(is_active=True)),
            total_distance=Sum('distance'),
            total_fare=Sum('fare')
        )

        context.update({
            "total_routes": stats.get("total_routes", 0),
            "active_routes": stats.get("active_routes", 0),
            "total_distance": stats.get("total_distance", 0),
            "total_fare": stats.get("total_fare", 0),
            "filter_form": RouteFilterForm(self.request.GET),
        })
        return context


class RouteCreateView( StaffManagementRequiredMixin, CreateView):
    model = Route
    form_class = RouteForm
    template_name = 'transport/route/route_form.html'

    def form_valid(self, form):
        # Set the institution automatically
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, "Route created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('transport:route_list')

class RouteUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = Route
    form_class = RouteForm
    template_name = 'transport/route/route_form.html'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Route.objects.filter(institution=institution)

    def form_valid(self, form):
        messages.success(self.request, "Route updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('transport:route_list')
    
    
class RouteDetailView( StaffManagementRequiredMixin, DetailView):
    model = Route
    template_name = 'transport/route/route_detail.html'
    context_object_name = 'route'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Route.objects.filter(institution=institution)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        route = self.get_object()
        context['stops'] = route.stops.order_by('sequence')  # use related_name 'stops'
        return context


class RouteDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = Route
    template_name = 'transport/route/route_confirm_delete.html'
    context_object_name = 'route'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Route.objects.filter(institution=institution)

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Route deleted successfully.")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('transport:route_list')

class RouteExportView( StaffManagementRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get("format", "csv").lower()
        institution = get_user_institution(request.user)
        
        queryset = Route.objects.filter(institution=institution).order_by('name')

        # Apply filters
        search = request.GET.get('search')
        status = request.GET.get('status')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(start_point__icontains=search) |
                Q(end_point__icontains=search)
            )
        
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        filename = f"routes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        rows = []
        for route in queryset:
            rows.append({
                "name": route.name,
                "start_point": route.start_point,
                "end_point": route.end_point,
                "distance": f"{route.distance} km",
                "estimated_time": str(route.estimated_time).split('.')[0] if route.estimated_time else "N/A",
                "fare": f"₹{route.fare}",
                "status": "Active" if route.is_active else "Inactive",
                "stops_count": route.routestop_set.count(),
                "created_at": route.created_at.strftime("%Y-%m-%d"),
            })

        organization = institution

        if format_type == "csv":
            return self.export_csv(rows, filename, organization)
        elif format_type == "excel":
            return self.export_excel(rows, filename, organization)
        elif format_type == "pdf":
            return self.export_pdf(rows, filename, organization, queryset.count())
        return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, rows, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        # Headers
        writer.writerow([
            "Route Name", "Start Point", "End Point", "Distance", 
            "Estimated Time", "Fare", "Status", "Stops Count", "Created Date"
        ])

        # Data rows
        for row in rows:
            writer.writerow([
                row["name"],
                row["start_point"],
                row["end_point"],
                row["distance"],
                row["estimated_time"],
                row["fare"],
                row["status"],
                row["stops_count"],
                row["created_at"],
            ])

        # Summary
        writer.writerow([])
        writer.writerow(["Total Records:", len(rows)])
        active_count = len([r for r in rows if r["status"] == "Active"])
        writer.writerow(["Active Records:", active_count])
        writer.writerow(["Organization:", organization.name if organization else "N/A"])
        writer.writerow(["Export Date:", timezone.now().strftime("%Y-%m-%d %H:%M")])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, rows, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Routes")

            # Header format
            header_format = workbook.add_format({
                "bold": True, "bg_color": "#2c3e50", "font_color": "white",
                "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True
            })

            headers = [
                "Route Name", "Start Point", "End Point", "Distance", 
                "Estimated Time", "Fare", "Status", "Stops Count", "Created Date"
            ]

            # Write headers
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            # Write data
            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data["name"])
                worksheet.write(row_idx, 1, row_data["start_point"])
                worksheet.write(row_idx, 2, row_data["end_point"])
                worksheet.write(row_idx, 3, row_data["distance"])
                worksheet.write(row_idx, 4, row_data["estimated_time"])
                worksheet.write(row_idx, 5, row_data["fare"])
                worksheet.write(row_idx, 6, row_data["status"])
                worksheet.write(row_idx, 7, row_data["stops_count"])
                worksheet.write(row_idx, 8, row_data["created_at"])

            # Column widths
            worksheet.set_column("A:A", 25)  # Route Name
            worksheet.set_column("B:B", 25)  # Start Point
            worksheet.set_column("C:C", 25)  # End Point
            worksheet.set_column("D:D", 12)  # Distance
            worksheet.set_column("E:E", 15)  # Estimated Time
            worksheet.set_column("F:F", 12)  # Fare
            worksheet.set_column("G:G", 10)  # Status
            worksheet.set_column("H:H", 12)  # Stops Count
            worksheet.set_column("I:I", 12)  # Created Date

            # Summary
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
            "title": "Routes Export",
            "columns": [
                {"name": "Route Name", "width": "18%"},
                {"name": "Start Point", "width": "18%"},
                {"name": "End Point", "width": "18%"},
                {"name": "Distance", "width": "10%"},
                {"name": "Est. Time", "width": "12%"},
                {"name": "Fare", "width": "8%"},
                {"name": "Status", "width": "8%"},
                {"name": "Stops", "width": "6%"},
                {"name": "Created", "width": "10%"},
            ],
        }
        pdf_bytes = render_to_pdf("transport/export/routes_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)