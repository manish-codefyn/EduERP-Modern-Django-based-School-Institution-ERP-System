import csv
import xlsxwriter
from io import BytesIO, StringIO
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy ,reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View,TemplateView

from apps.core.mixins import StaffManagementRequiredMixin
from apps.core.utils import get_user_institution
from utils.utils import render_to_pdf, export_pdf_response

from .models import Vehicle, MaintenanceRecord
from .forms import VehicleForm, VehicleFilterForm,MaintenanceRecordForm

from django.views.generic import TemplateView
from django.db.models.functions import TruncMonth
from django.db.models import Sum
from .models import Vehicle, Route, StudentTransport, TransportAttendance, MaintenanceRecord
from datetime import date


class TransportDashboardView(StaffManagementRequiredMixin,TemplateView):
    template_name = "transport/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Vehicles count by type
        vehicle_data = Vehicle.objects.values('vehicle_type').annotate(total=Count('id'))
        context['vehicle_labels'] = [v['vehicle_type'].capitalize() for v in vehicle_data]
        context['vehicle_counts'] = [v['total'] for v in vehicle_data]

        # Students per route
        route_data = StudentTransport.objects.values('transport_assignment__route__name') \
            .annotate(total_students=Count('id'))
        context['route_labels'] = [r['transport_assignment__route__name'] for r in route_data]
        context['route_counts'] = [r['total_students'] for r in route_data]

        # Maintenance cost per month (current year)
        current_year = date.today().year
        maintenance_data = (
            MaintenanceRecord.objects
            .filter(date__year=current_year)
            .annotate(month=TruncMonth('date'))
            .values('month')
            .annotate(total_cost=Sum('cost'))
            .order_by('month')
        )
        context['maintenance_labels'] = [m['month'].strftime('%b') for m in maintenance_data]  # Jan, Feb...
        context['maintenance_costs'] = [float(m['total_cost']) for m in maintenance_data]

        # Attendance summary for today
        today = date.today()
        attendance_data = TransportAttendance.objects.filter(date=today) \
            .values('pickup_status').annotate(count=Count('id'))
        status_dict = {status: 0 for status in ['present', 'absent', 'late']}
        for a in attendance_data:
            status_dict[a['pickup_status']] = a['count']
        context['attendance_labels'] = list(status_dict.keys())
        context['attendance_counts'] = list(status_dict.values())

        # Overall Stats for top cards
        context['total_vehicles'] = Vehicle.objects.count()
        context['active_routes'] = route_data.count() if route_data else 0
        context['total_students'] = StudentTransport.objects.count()
        context['monthly_cost'] = sum([float(m['total_cost']) for m in maintenance_data]) if maintenance_data else 0

        return context

    

class VehicleListView(StaffManagementRequiredMixin, ListView):
    model = Vehicle
    template_name = 'transport/vehicle_list.html'
    context_object_name = 'vehicles'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        institution = get_user_institution(user)
        if institution:
            queryset = queryset.filter(institution=institution)
        
        self.filter_form = VehicleFilterForm(self.request.GET, request=self.request)
        if self.filter_form.is_valid():
            vehicle_type = self.filter_form.cleaned_data.get('vehicle_type')
            fuel_type = self.filter_form.cleaned_data.get('fuel_type')
            status = self.filter_form.cleaned_data.get('status')
            date_from = self.filter_form.cleaned_data.get('date_from')
            date_to = self.filter_form.cleaned_data.get('date_to')
            
            if vehicle_type:
                queryset = queryset.filter(vehicle_type=vehicle_type)
            
            if fuel_type:
                queryset = queryset.filter(fuel_type=fuel_type)
            
            if status == 'active':
                queryset = queryset.filter(is_active=True)
            elif status == 'inactive':
                queryset = queryset.filter(is_active=False)
            
            if date_from:
                queryset = queryset.filter(registration_date__gte=date_from)
            
            if date_to:
                queryset = queryset.filter(registration_date__lte=date_to)
        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(vehicle_number__icontains=search_query) |
                Q(make__icontains=search_query) |
                Q(model__icontains=search_query) |
                Q(insurance_number__icontains=search_query)
            )
        
        return queryset.select_related('institution').order_by('vehicle_number')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context['filter_form'] = getattr(self, 'filter_form', VehicleFilterForm(request=self.request))
        
        queryset = self.get_queryset()
        context['total_vehicles'] = queryset.count()
        context['active_vehicles'] = queryset.filter(is_active=True).count()
        context['inactive_vehicles'] = queryset.filter(is_active=False).count()
        
        vehicle_type_stats = queryset.values('vehicle_type').annotate(count=Count('id'))
        context['vehicle_type_stats'] = {stat['vehicle_type']: stat['count'] for stat in vehicle_type_stats}
        
        fuel_type_stats = queryset.values('fuel_type').annotate(count=Count('id'))
        context['fuel_type_stats'] = {stat['fuel_type']: stat['count'] for stat in fuel_type_stats}
        
        total_capacity = queryset.aggregate(Sum('capacity'))['capacity__sum'] or 0
        context['total_capacity'] = total_capacity
        
        context['default_date_from'] = self.request.GET.get('date_from', (timezone.now() - timedelta(days=365)).strftime('%Y-%m-%d'))
        context['default_date_to'] = self.request.GET.get('date_to', timezone.now().strftime('%Y-%m-%d'))
        
        return context

class VehicleCreateView(StaffManagementRequiredMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'transport/vehicle_form.html'
    success_url = reverse_lazy('transport:vehicle_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        user = self.request.user
        institution = get_user_institution(user)
        
        if institution:
            form.instance.institution = institution
        
        messages.success(self.request, "Vehicle created successfully.")
        return super().form_valid(form)

class VehicleDetailView( StaffManagementRequiredMixin, DetailView):
    model = Vehicle
    template_name = 'transport/vehicle_detail.html'
    context_object_name = 'vehicle'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehicle = self.get_object()
        context['maintenance_records'] = MaintenanceRecord.objects.filter(vehicle=vehicle).order_by('-date')
        return context

class VehicleUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'transport/vehicle_form.html'
    success_url = reverse_lazy('transport:vehicle_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, "Vehicle updated successfully.")
        return super().form_valid(form)

class VehicleDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = Vehicle
    template_name = 'transport/vehicle_confirm_delete.html'
    success_url = reverse_lazy('transport:vehicle_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Vehicle deleted successfully.")
        return super().delete(request, *args, **kwargs)


class VehicleExportView( StaffManagementRequiredMixin, ListView):
    model = Vehicle
    context_object_name = 'vehicles'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Vehicle.objects.filter(institution=institution)
    
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        queryset = self.get_queryset()
        
        form = VehicleFilterForm(request.GET, request=request)
        if form.is_valid():
            vehicle_type = form.cleaned_data.get('vehicle_type')
            fuel_type = form.cleaned_data.get('fuel_type')
            status = form.cleaned_data.get('status')
            
            if vehicle_type:
                queryset = queryset.filter(vehicle_type=vehicle_type)
            if fuel_type:
                queryset = queryset.filter(fuel_type=fuel_type)
            if status == 'active':
                queryset = queryset.filter(is_active=True)
            elif status == 'inactive':
                queryset = queryset.filter(is_active=False)
        
        filename = f"vehicles_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        rows = []
        for vehicle in queryset:
            rows.append({
                "vehicle_number": vehicle.vehicle_number,
                "vehicle_type": vehicle.get_vehicle_type_display(),
                "make": vehicle.make,
                "model": vehicle.model,
                "year": vehicle.year,
                "color": vehicle.color,
                "capacity": vehicle.capacity,
                "fuel_type": vehicle.get_fuel_type_display(),
                "insurance_number": vehicle.insurance_number,
                "insurance_expiry": vehicle.insurance_expiry.strftime('%Y-%m-%d') if vehicle.insurance_expiry else 'N/A',
                "registration_date": vehicle.registration_date.strftime('%Y-%m-%d'),
                "registration_expiry": vehicle.registration_expiry.strftime('%Y-%m-%d'),
                "status": "Active" if vehicle.is_active else "Inactive",
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
            'Vehicle Number', 'Type', 'Make', 'Model', 'Year', 'Color', 
            'Capacity', 'Fuel Type', 'Insurance No', 'Insurance Expiry',
            'Registration Date', 'Registration Expiry', 'Status'
        ])
        
        for row in rows:
            writer.writerow([
                row['vehicle_number'],
                row['vehicle_type'],
                row['make'],
                row['model'],
                row['year'],
                row['color'],
                row['capacity'],
                row['fuel_type'],
                row['insurance_number'],
                row['insurance_expiry'],
                row['registration_date'],
                row['registration_expiry'],
                row['status'],
            ])
        
        writer.writerow([])
        writer.writerow(['Total Vehicles:', len(rows)])
        
        active_count = len([r for r in rows if r['status'] == 'Active'])
        writer.writerow(['Active Vehicles:', active_count])
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    def export_excel(self, rows, filename, organization):
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Vehicles')
            
            header_format = workbook.add_format({
                'bold': True, 'bg_color': '#3b5998', 'font_color': 'white',
                'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True
            })
            
            headers = [
                'Vehicle Number', 'Type', 'Make', 'Model', 'Year', 'Color', 
                'Capacity', 'Fuel Type', 'Insurance No', 'Insurance Expiry',
                'Registration Date', 'Registration Expiry', 'Status'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data['vehicle_number'])
                worksheet.write(row_idx, 1, row_data['vehicle_type'])
                worksheet.write(row_idx, 2, row_data['make'])
                worksheet.write(row_idx, 3, row_data['model'])
                worksheet.write(row_idx, 4, row_data['year'])
                worksheet.write(row_idx, 5, row_data['color'])
                worksheet.write(row_idx, 6, row_data['capacity'])
                worksheet.write(row_idx, 7, row_data['fuel_type'])
                worksheet.write(row_idx, 8, row_data['insurance_number'])
                worksheet.write(row_idx, 9, row_data['insurance_expiry'])
                worksheet.write(row_idx, 10, row_data['registration_date'])
                worksheet.write(row_idx, 11, row_data['registration_expiry'])
                worksheet.write(row_idx, 12, row_data['status'])
            
            worksheet.set_column('A:A', 15)
            worksheet.set_column('B:B', 12)
            worksheet.set_column('C:D', 15)
            worksheet.set_column('E:E', 8)
            worksheet.set_column('F:F', 10)
            worksheet.set_column('G:G', 10)
            worksheet.set_column('H:H', 12)
            worksheet.set_column('I:I', 20)
            worksheet.set_column('J:K', 15)
            worksheet.set_column('L:L', 18)
            worksheet.set_column('M:M', 10)
            
            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, 'Total Vehicles:')
            worksheet.write(summary_row, 1, len(rows))
            
            active_count = len([r for r in rows if r['status'] == 'Active'])
            worksheet.write(summary_row + 1, 0, 'Active Vehicles:')
            worksheet.write(summary_row + 1, 1, active_count)
            
            worksheet.write(summary_row + 3, 0, 'Organization:')
            worksheet.write(summary_row + 3, 1, organization.name if organization else 'N/A')
            
            worksheet.write(summary_row + 4, 0, 'Export Date:')
            worksheet.write(summary_row + 4, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))
        
        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response
    
    def export_pdf(self, rows, filename, organization, total_count):
        active_count = len([r for r in rows if r['status'] == 'Active'])
        
        context = {
            "vehicles": rows,
            "total_count": total_count,
            "active_count": active_count,
            "export_date": timezone.now(),
            "organization": organization,
            "title": "Vehicle Export",
            "columns": [
                {'name': 'Vehicle No', 'width': '15%'},
                {'name': 'Type', 'width': '10%'},
                {'name': 'Make/Model', 'width': '20%'},
                {'name': 'Year', 'width': '8%'},
                {'name': 'Capacity', 'width': '10%'},
                {'name': 'Fuel Type', 'width': '12%'},
                {'name': 'Status', 'width': '10%'},
            ]
        }
        
        pdf_bytes = render_to_pdf("transport/export/vehicle_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)
    

class VehicleMaintenanceCreateView( StaffManagementRequiredMixin, CreateView):
    model = MaintenanceRecord
    form_class = MaintenanceRecordForm
    template_name = 'transport/maintenance_form.html'

    def form_valid(self, form):
        vehicle = get_object_or_404(Vehicle, pk=self.kwargs['pk'])
        form.instance.vehicle = vehicle
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, "Maintenance record added successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('transport:vehicle_detail', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the vehicle to context
        vehicle = get_object_or_404(Vehicle, pk=self.kwargs['pk'])
        context['vehicle'] = vehicle
        context['page_title'] = f"Add Maintenance Record for {vehicle.vehicle_number}"
        context['breadcrumbs'] = [
            {'title': 'Vehicles', 'url': reverse('transport:vehicle_list')},
            {'title': vehicle.vehicle_number, 'url': reverse('transport:vehicle_detail', kwargs={'pk': vehicle.pk})},
            {'title': 'Add Maintenance'}
        ]
        return context


class VehicleMaintenanceUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = MaintenanceRecord
    form_class = MaintenanceRecordForm
    template_name = 'transport/maintenance_form.html'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return MaintenanceRecord.objects.filter(institution=institution)

    def form_valid(self, form):
        messages.success(self.request, "Maintenance record updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('transport:vehicle_detail', kwargs={'pk': self.object.vehicle.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add the vehicle to context
        vehicle = get_object_or_404(Vehicle, pk=self.kwargs['pk'])
        context['vehicle'] = vehicle
        context['page_title'] = f"Add Maintenance Record for {vehicle.vehicle_number}"
        context['breadcrumbs'] = [
            {'title': 'Vehicles', 'url': reverse('transport:vehicle_list')},
            {'title': vehicle.vehicle_number, 'url': reverse('transport:vehicle_detail', kwargs={'pk': vehicle.pk})},
            {'title': 'Add Maintenance'}
        ]
        return context

class VehicleMaintenanceDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = MaintenanceRecord
    template_name = 'transport/maintenance_confirm_delete.html'
    context_object_name = 'maintenance_record'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return MaintenanceRecord.objects.filter(institution=institution)

    def get_success_url(self):
        return reverse('transport:vehicle_detail', kwargs={'pk': self.object.vehicle.pk})


class VehicleToggleStatusView( StaffManagementRequiredMixin, View):
    def post(self, request, pk):
        vehicle = get_object_or_404(Vehicle, pk=pk)
        vehicle.is_active = not vehicle.is_active
        vehicle.save()
        status = "activated" if vehicle.is_active else "deactivated"
        messages.success(request, f"Vehicle {status} successfully.")
        return redirect('transport:vehicle_detail', pk=vehicle.pk)
    

class VehicleMaintenanceDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = MaintenanceRecord
    template_name = 'transport/maintenance_confirm_delete.html'
    context_object_name = 'maintenance_record'

    def get_queryset(self):
        """
        Limit deletion to the user's institution.
        """
        institution = get_user_institution(self.request.user)
        return MaintenanceRecord.objects.filter(institution=institution)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        vehicle_pk = self.object.vehicle.pk
        messages.success(request, f"Maintenance record for {self.object.vehicle.vehicle_number} deleted successfully.")
        self.object.delete()
        return redirect('transport:vehicle_detail', pk=vehicle_pk)