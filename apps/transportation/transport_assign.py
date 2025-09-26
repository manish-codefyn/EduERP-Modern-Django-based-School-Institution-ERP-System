
# apps/transportation/views.py
import csv
from io import StringIO, BytesIO
from datetime import datetime
import xlsxwriter
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta


from utils.utils import render_to_pdf, export_pdf_response  # your PDF utils

from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView,View
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import StaffManagementRequiredMixin
from .models import TransportAssignment
from .forms import TransportAssignmentForm,TransportAssignmentFilterForm
from apps.core.utils import get_user_institution


class TransportAssignmentListView( StaffManagementRequiredMixin, ListView):
    model = TransportAssignment
    template_name = 'transport/assign/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        institution = get_user_institution(user)
        if institution:
            queryset = queryset.filter(institution=institution)
        
        self.filter_form = TransportAssignmentFilterForm(self.request.GET, request=self.request)
        if self.filter_form.is_valid():
            vehicle = self.filter_form.cleaned_data.get('vehicle')
            driver = self.filter_form.cleaned_data.get('driver')
            route = self.filter_form.cleaned_data.get('route')
            status = self.filter_form.cleaned_data.get('status')
            date_from = self.filter_form.cleaned_data.get('date_from')
            date_to = self.filter_form.cleaned_data.get('date_to')
            
            if vehicle:
                queryset = queryset.filter(vehicle=vehicle)
            if driver:
                queryset = queryset.filter(driver=driver)
            if route:
                queryset = queryset.filter(route=route)
            if date_from:
                queryset = queryset.filter(start_date__gte=date_from)
            if date_to:
                queryset = queryset.filter(start_date__lte=date_to)
            
            # Handle status filtering
            today = timezone.now().date()
            if status == 'active':
                queryset = queryset.filter(is_active=True, start_date__lte=today).filter(
                    Q(end_date__isnull=True) | Q(end_date__gte=today)
                )
            elif status == 'inactive':
                queryset = queryset.filter(is_active=False)
            elif status == 'expired':
                queryset = queryset.filter(is_active=True, end_date__lt=today)
            elif status == 'scheduled':
                queryset = queryset.filter(is_active=True, start_date__gt=today)
        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(vehicle__vehicle_number__icontains=search_query) |
                Q(driver__name__icontains=search_query) |
                Q(route__name__icontains=search_query)
            )
        
        return queryset.select_related('vehicle', 'driver', 'route', 'institution').order_by('-start_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context['filter_form'] = getattr(self, 'filter_form', TransportAssignmentFilterForm(request=self.request))
        
        queryset = self.get_queryset()
        context['total_assignments'] = queryset.count()
        
        # Calculate status counts
        today = timezone.now().date()
        context['active_assignments'] = queryset.filter(
            is_active=True, start_date__lte=today
        ).filter(Q(end_date__isnull=True) | Q(end_date__gte=today)).count()
        
        context['inactive_assignments'] = queryset.filter(is_active=False).count()
        context['expired_assignments'] = queryset.filter(is_active=True, end_date__lt=today).count()
        context['scheduled_assignments'] = queryset.filter(is_active=True, start_date__gt=today).count()
        
        # Vehicle type distribution
        vehicle_stats = queryset.values('vehicle__vehicle_type').annotate(count=Count('id'))
        context['vehicle_type_stats'] = {stat['vehicle__vehicle_type']: stat['count'] for stat in vehicle_stats}
        
        context['default_date_from'] = self.request.GET.get('date_from', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        context['default_date_to'] = self.request.GET.get('date_to', (timezone.now() + timedelta(days=30)).strftime('%Y-%m-%d'))
        
        return context

class TransportAssignmentCreateView( StaffManagementRequiredMixin, CreateView):
    model = TransportAssignment
    form_class = TransportAssignmentForm
    template_name = 'transport/assign/assignment_form.html'
    success_url = reverse_lazy('transport:assignment_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        user = self.request.user
        institution = get_user_institution(user)
        
        if institution:
            form.instance.institution = institution
        
        # Check for overlapping assignments
        vehicle = form.cleaned_data['vehicle']
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date'] or start_date + timedelta(days=365)  # Default 1 year
        
        overlapping = TransportAssignment.objects.filter(
            vehicle=vehicle,
            is_active=True
        ).filter(
            Q(start_date__lte=end_date) &
            Q(Q(end_date__isnull=True) | Q(end_date__gte=start_date))
        ).exclude(pk=form.instance.pk if form.instance.pk else None)
        
        if overlapping.exists():
            form.add_error(None, "This vehicle already has an assignment for the selected date range.")
            return self.form_invalid(form)
        
        messages.success(self.request, "Transport assignment created successfully.")
        return super().form_valid(form)

class TransportAssignmentDetailView( StaffManagementRequiredMixin, DetailView):
    model = TransportAssignment
    template_name = 'transport/assign/assignment_detail.html'
    context_object_name = 'assignment'

class TransportAssignmentUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = TransportAssignment
    form_class = TransportAssignmentForm
    template_name = 'transport/assign/assignment_form.html'
    success_url = reverse_lazy('transport:assignment_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, "Transport assignment updated successfully.")
        return super().form_valid(form)

class TransportAssignmentDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = TransportAssignment
    template_name = 'transport/assign/assignment_confirm_delete.html'
    success_url = reverse_lazy('transport:assignment_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Transport assignment deleted successfully.")
        return super().delete(request, *args, **kwargs)

class TransportAssignmentExportView( StaffManagementRequiredMixin, ListView):
    model = TransportAssignment
    context_object_name = 'assignments'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return TransportAssignment.objects.filter(institution=institution).select_related('vehicle', 'driver', 'route')
    
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        queryset = self.get_queryset()
        
        form = TransportAssignmentFilterForm(request.GET, request=request)
        if form.is_valid():
            vehicle = form.cleaned_data.get('vehicle')
            driver = form.cleaned_data.get('driver')
            route = form.cleaned_data.get('route')
            status = form.cleaned_data.get('status')
            
            if vehicle:
                queryset = queryset.filter(vehicle=vehicle)
            if driver:
                queryset = queryset.filter(driver=driver)
            if route:
                queryset = queryset.filter(route=route)
        
        filename = f"transport_assignments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        rows = []
        for assignment in queryset:
            rows.append({
                "vehicle_number": assignment.vehicle.vehicle_number,
                "vehicle_type": assignment.vehicle.get_vehicle_type_display(),
                "driver_name": assignment.driver.user.get_full_name(),
                "driver_license": assignment.driver.license_number,
                "route_name": assignment.route.name,
                "start_date": assignment.start_date.strftime('%Y-%m-%d'),
                "end_date": assignment.end_date.strftime('%Y-%m-%d') if assignment.end_date else 'Not set',
                "status": assignment.current_status.title(),
                "created_at": assignment.created_at.strftime('%Y-%m-%d %H:%M'),
            })

        organization = get_user_institution(request.user)
        
        if format_type == 'csv':
            return self.export_csv(rows, filename, organization)
        elif format_type == 'excel':
            return self.export_excel(rows, filename, organization)
        elif format_type == 'pdf':
            return self.export_pdf(rows, filename, organization, queryset.count())
        else:
            return HttpResponse("Invalid format specified", status=400)
    
    def export_csv(self, rows, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)
        
        writer.writerow([
            'Vehicle Number', 'Vehicle Type', 'Driver Name', 'Driver License',
            'Route Name', 'Start Date', 'End Date', 'Status', 'Created At'
        ])
        
        for row in rows:
            writer.writerow([
                row['vehicle_number'],
                row['vehicle_type'],
                row['driver_name'],
                row['driver_license'],
                row['route_name'],
                row['start_date'],
                row['end_date'],
                row['status'],
                row['created_at'],
            ])
        
        writer.writerow([])
        writer.writerow(['Total Assignments:', len(rows)])
        
        active_count = len([r for r in rows if r['status'] == 'Active'])
        expired_count = len([r for r in rows if r['status'] == 'Expired'])
        
        writer.writerow(['Active Assignments:', active_count])
        writer.writerow(['Expired Assignments:', expired_count])
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    def export_excel(self, rows, filename, organization):
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Transport Assignments')
            
            header_format = workbook.add_format({
                'bold': True, 'bg_color': '#3b5998', 'font_color': 'white',
                'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True
            })
            
            headers = [
                'Vehicle Number', 'Vehicle Type', 'Driver Name', 'Driver License',
                'Route Name', 'Start Date', 'End Date', 'Status', 'Created At'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data['vehicle_number'])
                worksheet.write(row_idx, 1, row_data['vehicle_type'])
                worksheet.write(row_idx, 2, row_data['driver_name'])
                worksheet.write(row_idx, 3, row_data['driver_license'])
                worksheet.write(row_idx, 4, row_data['route_name'])
                worksheet.write(row_idx, 5, row_data['start_date'])
                worksheet.write(row_idx, 6, row_data['end_date'])
                worksheet.write(row_idx, 7, row_data['status'])
                worksheet.write(row_idx, 8, row_data['created_at'])
            
            worksheet.set_column('A:A', 15)
            worksheet.set_column('B:B', 12)
            worksheet.set_column('C:C', 20)
            worksheet.set_column('D:D', 15)
            worksheet.set_column('E:E', 20)
            worksheet.set_column('F:G', 12)
            worksheet.set_column('H:H', 12)
            worksheet.set_column('I:I', 16)
            
            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, 'Total Assignments:')
            worksheet.write(summary_row, 1, len(rows))
            
            active_count = len([r for r in rows if r['status'] == 'Active'])
            expired_count = len([r for r in rows if r['status'] == 'Expired'])
            
            summary_row += 1
            worksheet.write(summary_row, 0, 'Active Assignments:')
            worksheet.write(summary_row, 1, active_count)
            
            summary_row += 1
            worksheet.write(summary_row, 0, 'Expired Assignments:')
            worksheet.write(summary_row, 1, expired_count)
            
            summary_row += 2
            worksheet.write(summary_row, 0, 'Organization:')
            worksheet.write(summary_row, 1, organization.name if organization else 'N/A')
            
            summary_row += 1
            worksheet.write(summary_row, 0, 'Export Date:')
            worksheet.write(summary_row, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))
        
        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response
    
    def export_pdf(self, rows, filename, organization, total_count):
        active_count = len([r for r in rows if r['status'] == 'Active'])
        expired_count = len([r for r in rows if r['status'] == 'Expired'])
        
        context = {
            "assignments": rows,
            "total_count": total_count,
            "active_count": active_count,
            "expired_count": expired_count,
            "export_date": timezone.now(),
            "organization": organization,
            "title": "Transport Assignments Export",
            "columns": [
                {'name': 'Vehicle No', 'width': '15%'},
                {'name': 'Driver', 'width': '20%'},
                {'name': 'Route', 'width': '20%'},
                {'name': 'Start Date', 'width': '12%'},
                {'name': 'End Date', 'width': '12%'},
                {'name': 'Status', 'width': '10%'},
            ]
        }
        
        pdf_bytes = render_to_pdf("transport/export/assignment_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)
    
class TransportAssignmentToggleStatusView( StaffManagementRequiredMixin, View):
    def post(self, request, pk):
        assignment = get_object_or_404(TransportAssignment, pk=pk)
        assignment.is_active = not assignment.is_active
        assignment.save()
        
        status = "activated" if assignment.is_active else "deactivated"
        messages.success(request, f"Assignment {status} successfully.")
        return redirect('transport:assignment_detail', pk=assignment.pk)