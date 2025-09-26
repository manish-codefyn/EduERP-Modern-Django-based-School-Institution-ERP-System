# apps/transport/views/route_stop_views.py
import csv
from io import StringIO, BytesIO
from datetime import datetime
import xlsxwriter
from django.http import HttpResponse,JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView,View
from django.contrib.auth.mixins import LoginRequiredMixin

from utils.utils import render_to_pdf, export_pdf_response  # your PDF utils
from apps.core.mixins import StaffManagementRequiredMixin
from apps.core.utils import get_user_institution
from .models import RouteStop,Route
from .forms import RouteStopForm, RouteStopFilterForm

class RouteStopListView( StaffManagementRequiredMixin, ListView):
    model = RouteStop
    template_name = 'transport/route_stop/route_stop_list.html'
    context_object_name = 'stops'
    paginate_by = 25

    def get_queryset(self):
        institution = get_user_institution(self.request.user)

        # Filter RouteStops by institution through related Route
        queryset = RouteStop.objects.select_related('route').filter(
            route__institution=institution  # Corrected
        ).order_by('route__name', 'sequence')  # Use sequence instead of 'order'

        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(route__name__icontains=search) |
                Q(name__icontains=search) |
                Q(address__icontains=search)
            )

        # Route filter
        route_id = self.request.GET.get('route')
        if route_id:
            queryset = queryset.filter(route_id=route_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)

        # Get available routes for filter dropdown
        context['available_routes'] = Route.objects.filter(
            institution=institution, is_active=True
        )

        # Statistics
        stats = RouteStop.objects.filter(route__institution=institution).aggregate(
            total_stops=Count('id'),
            # Example: you can add active/inactive if you have a field for it
        )

        context.update({
            "total_stops": stats.get("total_stops", 0),
            "filter_form": RouteStopFilterForm(self.request.GET, request=self.request),
        })
        return context

class RouteStopCreateView( StaffManagementRequiredMixin, CreateView):
    model = RouteStop
    form_class = RouteStopForm
    template_name = 'transport/route_stop/route_stop_form.html'

    def form_valid(self, form):
        # Automatically set sequence if not provided
        if not form.instance.sequence:
            last_sequence = RouteStop.objects.filter(
                route=form.instance.route
            ).aggregate(last_seq=Count('id'))['last_seq'] or 0
            form.instance.sequence = last_sequence + 1

        messages.success(self.request, "Route stop created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('transport:route_stop_list')
    
class RouteStopUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = RouteStop
    form_class = RouteStopForm
    template_name = 'transport/route_stop/route_stop_form.html'

    def get_queryset(self):
        # Limit to stops where the route belongs to the user's institution
        institution = get_user_institution(self.request.user)
        return RouteStop.objects.filter(route__institution=institution)

    def form_valid(self, form):
        messages.success(self.request, "Route stop updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('transport:route_stop_list')

class RouteStopDetailView( StaffManagementRequiredMixin, DetailView):
    model = RouteStop
    template_name = 'transport/route_stop/route_stop_detail.html'
    context_object_name = 'route_stop'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return RouteStop.objects.select_related('route', 'stop').filter(institution=institution)
    

class RouteStopDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = RouteStop
    template_name = 'transport/route_stop/route_stop_confirm_delete.html'
    context_object_name = 'route_stop'

    def get_queryset(self):
        # Limit deletion to RouteStops where the related Route belongs to the user's institution
        institution = get_user_institution(self.request.user)
        return RouteStop.objects.filter(route__institution=institution)

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Route stop deleted successfully.")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('transport:route_stop_list')
    
    
class RouteStopExportView( StaffManagementRequiredMixin, ListView):
    model = RouteStop
    context_object_name = "route_stops"

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return RouteStop.objects.select_related(
            "route", "stop"
        ).filter(institution=institution).order_by('route__name', 'order')

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get("format", "csv").lower()
        queryset = self.get_queryset()

        # Apply filters
        form = RouteStopFilterForm(request.GET, request=request)
        if form.is_valid():
            if form.cleaned_data.get("status") == "active":
                queryset = queryset.filter(is_active=True)
            elif form.cleaned_data.get("status") == "inactive":
                queryset = queryset.filter(is_active=False)
            
            route_id = form.cleaned_data.get("route")
            if route_id:
                queryset = queryset.filter(route_id=route_id)

        filename = f"route_stops_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        rows = []
        for stop in queryset:
            rows.append({
                "route": str(stop.route),
                "stop_name": str(stop.stop),
                "stop_address": stop.stop.address if stop.stop.address else "N/A",
                "order": stop.order,
                "arrival_time": stop.arrival_time.strftime("%H:%M") if stop.arrival_time else "N/A",
                "departure_time": stop.departure_time.strftime("%H:%M") if stop.departure_time else "N/A",
                "distance_from_previous": f"{stop.distance_from_previous} km" if stop.distance_from_previous else "N/A",
                "estimated_time_from_previous": f"{stop.estimated_time_from_previous} min" if stop.estimated_time_from_previous else "N/A",
                "status": "Active" if stop.is_active else "Inactive",
            })

        organization = get_user_institution(request.user)

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
            "Route", "Stop Name", "Stop Address", "Order", 
            "Arrival Time", "Departure Time", "Distance", 
            "Estimated Time", "Status"
        ])

        # Data rows
        for row in rows:
            writer.writerow([
                row["route"],
                row["stop_name"],
                row["stop_address"],
                row["order"],
                row["arrival_time"],
                row["departure_time"],
                row["distance_from_previous"],
                row["estimated_time_from_previous"],
                row["status"],
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
            worksheet = workbook.add_worksheet("Route Stops")

            # Header format
            header_format = workbook.add_format({
                "bold": True, "bg_color": "#2c3e50", "font_color": "white",
                "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True
            })

            headers = [
                "Route", "Stop Name", "Stop Address", "Order", 
                "Arrival Time", "Departure Time", "Distance", 
                "Estimated Time", "Status"
            ]

            # Write headers
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            # Write data
            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data["route"])
                worksheet.write(row_idx, 1, row_data["stop_name"])
                worksheet.write(row_idx, 2, row_data["stop_address"])
                worksheet.write(row_idx, 3, row_data["order"])
                worksheet.write(row_idx, 4, row_data["arrival_time"])
                worksheet.write(row_idx, 5, row_data["departure_time"])
                worksheet.write(row_idx, 6, row_data["distance_from_previous"])
                worksheet.write(row_idx, 7, row_data["estimated_time_from_previous"])
                worksheet.write(row_idx, 8, row_data["status"])

            # Column widths
            worksheet.set_column("A:A", 25)  # Route
            worksheet.set_column("B:B", 25)  # Stop Name
            worksheet.set_column("C:C", 30)  # Stop Address
            worksheet.set_column("D:D", 8)   # Order
            worksheet.set_column("E:F", 12)  # Times
            worksheet.set_column("G:H", 15)  # Distance/Time
            worksheet.set_column("I:I", 10)  # Status

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
            "title": "Route Stops Export",
            "columns": [
                {"name": "Route", "width": "20%"},
                {"name": "Stop Name", "width": "18%"},
                {"name": "Address", "width": "20%"},
                {"name": "Order", "width": "6%"},
                {"name": "Arrival", "width": "8%"},
                {"name": "Departure", "width": "8%"},
                {"name": "Distance", "width": "8%"},
                {"name": "Est. Time", "width": "7%"},
                {"name": "Status", "width": "5%"},
            ],
        }
        pdf_bytes = render_to_pdf("transport/export/route_stops_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

class RouteStopReorderView( StaffManagementRequiredMixin, View):
    """View for reordering stops within a route"""
    
    def post(self, request, *args, **kwargs):
        route_id = request.POST.get('route_id')
        stop_order = request.POST.getlist('stop_order[]')
        
        institution = get_user_institution(request.user)
        
        try:
            with transaction.atomic():
                for index, stop_id in enumerate(stop_order, start=1):
                    RouteStop.objects.filter(
                        id=stop_id, 
                        route_id=route_id, 
                        institution=institution
                    ).update(order=index)
            
            messages.success(request, "Route stops reordered successfully.")
            return JsonResponse({'success': True})
        
        except Exception as e:
            messages.error(request, f"Error reordering stops: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})