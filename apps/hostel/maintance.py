from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q, Count
from io import StringIO, BytesIO
import csv
import xlsxwriter

from .models import MaintenanceRequest,Room
from .forms import MaintenanceRequestForm
from apps.core.utils import get_user_institution
from apps.core.mixins import FinanceAccessRequiredMixin, DirectorRequiredMixin
from utils.utils import render_to_pdf, export_pdf_response


class MaintenanceRequestListView(FinanceAccessRequiredMixin, ListView):
    model = MaintenanceRequest
    template_name = 'hostel/maintenance/maintenance_list.html'
    context_object_name = 'requests'
    paginate_by = 20
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = MaintenanceRequest.objects.filter(institution=institution).select_related(
            'hostel', 'room', 'requested_by', 'assigned_to'
        ).order_by('-requested_date')
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by priority if provided
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(requested_by__user__first_name__icontains=search) |
                Q(requested_by__user__last_name__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Statistics
        context['total_requests'] = MaintenanceRequest.objects.filter(institution=institution).count()
        context['pending_requests'] = MaintenanceRequest.objects.filter(
            institution=institution, status='pending'
        ).count()
        context['in_progress_requests'] = MaintenanceRequest.objects.filter(
            institution=institution, status='in_progress'
        ).count()
        context['completed_requests'] = MaintenanceRequest.objects.filter(
            institution=institution, status='completed'
        ).count()
        
        # Status and priority choices for filters
        context['status_choices'] = MaintenanceRequest.STATUS_CHOICES
        context['priority_choices'] = MaintenanceRequest.PRIORITY_CHOICES
        
        # Current filters
        context['current_status'] = self.request.GET.get('status', '')
        context['current_priority'] = self.request.GET.get('priority', '')
        context['current_search'] = self.request.GET.get('search', '')
        
        return context


class MaintenanceRequestCreateView(  CreateView):
    model = MaintenanceRequest
    form_class = MaintenanceRequestForm
    template_name = 'hostel/maintenance/maintenance_form.html'
    success_url = reverse_lazy('hostel:maintenance_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Maintenance Request'
        context['submit_text'] = 'Create Request'
        return context
    
    def form_valid(self, form):
        # Set the institution and requested_by before saving
        form.instance.institution = get_user_institution(self.request.user)

        # Get the staff member associated with the current user
        staff_member = getattr(self.request.user, 'staff_profile', None)  # <-- FIXED
        if not staff_member:
            # Handle case where user doesn't have a staff profile
            messages.error(self.request, 'You need a staff profile to create maintenance requests.')
            return self.form_invalid(form)

        form.instance.requested_by = staff_member
        messages.success(self.request, 'Maintenance request created successfully!')
        return super().form_valid(form)



class MaintenanceRequestUpdateView( FinanceAccessRequiredMixin, UpdateView):
    model = MaintenanceRequest
    form_class = MaintenanceRequestForm
    template_name = 'hostel/maintenance/maintenance_form.html'
    success_url = reverse_lazy('hostel:maintenance_list')
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return MaintenanceRequest.objects.filter(institution=institution)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Maintenance Request'
        context['submit_text'] = 'Update Request'
        return context
    
    def form_valid(self, form):
        # If status is being changed to completed, set completed_date
        if form.instance.status == 'completed' and not form.instance.completed_date:
            form.instance.completed_date = timezone.now()
        
        messages.success(self.request, 'Maintenance request updated successfully!')
        return super().form_valid(form)


class MaintenanceRequestDeleteView( DirectorRequiredMixin, DeleteView):
    model = MaintenanceRequest
    template_name = 'hostel/maintenance/maintenance_confirm_delete.html'
    success_url = reverse_lazy('hostel:maintenance_list')
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return MaintenanceRequest.objects.filter(institution=institution)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Maintenance request deleted successfully!')
        return super().delete(request, *args, **kwargs)


class MaintenanceRequestDetailView( FinanceAccessRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        maintenance_request = get_object_or_404(
            MaintenanceRequest, 
            id=kwargs['pk'],
            institution=get_user_institution(request.user)
        )
        # You can render a detail template here or return JSON for API
        return redirect('hostel:maintenance_list')


class MaintenanceRequestCompleteView( FinanceAccessRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        maintenance_request = get_object_or_404(
            MaintenanceRequest, 
            id=kwargs['pk'],
            institution=get_user_institution(request.user)
        )
        
        if maintenance_request.status != 'completed':
            maintenance_request.status = 'completed'
            maintenance_request.completed_date = timezone.now()
            maintenance_request.save()
            messages.success(request, f'Maintenance request marked as completed!')
        else:
            messages.warning(request, f'Maintenance request is already completed!')
        
        return redirect('hostel:maintenance_list')


class MaintenanceRequestExportView( FinanceAccessRequiredMixin, View):
    """
    Export Maintenance Request data in CSV, PDF, Excel formats
    """

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        status = request.GET.get("status")
        priority = request.GET.get("priority")

        institution = get_user_institution(request.user)
        qs = MaintenanceRequest.objects.filter(institution=institution).select_related(
            'hostel', 'room', 'requested_by', 'assigned_to'
        )

        if start_date:
            qs = qs.filter(requested_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(requested_date__date__lte=end_date)
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)

        qs = qs.order_by("-requested_date")

        filename_parts = ["maintenance_requests"]
        if start_date:
            filename_parts.append(f"from_{start_date}")
        if end_date:
            filename_parts.append(f"to_{end_date}")
        if status:
            filename_parts.append(f"status_{status}")
        if priority:
            filename_parts.append(f"priority_{priority}")
        filename = "_".join(filename_parts).lower()

        rows = []
        for request in qs:
            rows.append({
                "title": request.title,
                "description": request.description,
                "hostel": request.hostel.name if request.hostel else "N/A",
                "room": request.room.room_number if request.room else "N/A",
                "requested_by": request.requested_by.user.get_full_name() if request.requested_by else "N/A",
                "priority": request.get_priority_display(),
                "status": request.get_status_display(),
                "assigned_to": request.assigned_to.user.get_full_name() if request.assigned_to else "Not Assigned",
                "requested_date": request.requested_date.strftime("%Y-%m-%d %H:%M"),
                "completed_date": request.completed_date.strftime("%Y-%m-%d %H:%M") if request.completed_date else "-",
                "cost": f"${request.cost}" if request.cost else "Not Set",
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
            "Title", "Description", "Hostel", "Room", "Requested By", 
            "Priority", "Status", "Assigned To", "Requested Date", 
            "Completed Date", "Cost"
        ])

        for row in rows:
            writer.writerow([
                row["title"], row["description"], row["hostel"], row["room"],
                row["requested_by"], row["priority"], row["status"],
                row["assigned_to"], row["requested_date"], row["completed_date"],
                row["cost"]
            ])

        writer.writerow([])
        writer.writerow(["Total Requests:", len(rows)])
        writer.writerow(["Organization:", organization.name if organization else "N/A"])
        writer.writerow(["Export Date:", timezone.now().strftime("%Y-%m-%d %H:%M")])

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_pdf(self, rows, filename, organization, total_count):
        context = {
            "requests": rows,
            "total_count": total_count,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Maintenance Requests Export",
            "columns": [
                {"name": "Title", "width": "15%"},
                {"name": "Hostel", "width": "10%"},
                {"name": "Room", "width": "8%"},
                {"name": "Priority", "width": "8%"},
                {"name": "Status", "width": "10%"},
                {"name": "Requested By", "width": "12%"},
                {"name": "Requested Date", "width": "12%"},
                {"name": "Cost", "width": "10%"},
            ]
        }

        pdf_bytes = render_to_pdf("hostel/export/maintenance_requests_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

    def export_excel(self, rows, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            ws = workbook.add_worksheet("Maintenance Requests")

            header_fmt = workbook.add_format({"bold": True, "bg_color": "#3b5998", "font_color": "white"})

            headers = [
                "Title", "Description", "Hostel", "Room", "Requested By", 
                "Priority", "Status", "Assigned To", "Requested Date", 
                "Completed Date", "Cost"
            ]

            for col, h in enumerate(headers):
                ws.write(0, col, h, header_fmt)

            for i, r in enumerate(rows, start=1):
                ws.write(i, 0, r['title'])
                ws.write(i, 1, r['description'])
                ws.write(i, 2, r['hostel'])
                ws.write(i, 3, r['room'])
                ws.write(i, 4, r['requested_by'])
                ws.write(i, 5, r['priority'])
                ws.write(i, 6, r['status'])
                ws.write(i, 7, r['assigned_to'])
                ws.write(i, 8, r['requested_date'])
                ws.write(i, 9, r['completed_date'])
                ws.write(i, 10, r['cost'])

            ws.set_column("A:K", 15)
            ws.set_column("B:B", 25)  # Wider column for description

            summary_row = len(rows) + 2
            ws.write(summary_row, 0, "Total Requests:")
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
    
    

def load_rooms(request):
    """
    Loads rooms for a given hostel and returns them as a JSON response.
    """
    hostel_id = request.GET.get('hostel_id')
    try:
        # Filter rooms by the selected hostel ID
        rooms = Room.objects.filter(hostel_id=hostel_id).order_by('room_number')
        # Format the data for JSON: a list of objects with id and name
        data = [{'id': room.id, 'name': str(room)} for room in rooms]
        return JsonResponse(data, safe=False)
    except (ValueError, TypeError):
        # Handle cases where hostel_id is not a valid number
        return JsonResponse([], safe=False)