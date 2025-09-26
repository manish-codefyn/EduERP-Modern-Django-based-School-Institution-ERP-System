import csv
import xlsxwriter
from io import BytesIO, StringIO
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Avg, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View

from apps.core.mixins import StaffManagementRequiredMixin
from apps.core.utils import get_user_institution
from utils.utils import render_to_pdf, export_pdf_response

from .models import HrAttendance, Staff,Department,Designation
from .forms import AttendanceForm, AttendanceFilterForm



class AttendanceListView( StaffManagementRequiredMixin, ListView):
    model = HrAttendance
    template_name = 'hr/attendance/attendance_list.html'
    context_object_name = 'attendances'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter by user's institution
        institution = get_user_institution(user)
        if institution:
            queryset = queryset.filter(institution=institution)
        
        # Apply filters using AttendanceFilterForm
        self.filter_form = AttendanceFilterForm(self.request.GET, request=self.request)
        if self.filter_form.is_valid():
            staff = self.filter_form.cleaned_data.get('staff')
            date_from = self.filter_form.cleaned_data.get('date_from')
            date_to = self.filter_form.cleaned_data.get('date_to')
            status = self.filter_form.cleaned_data.get('status')
            
            if staff:
                queryset = queryset.filter(staff=staff)
            
            if date_from:
                queryset = queryset.filter(date__gte=date_from)
            
            if date_to:
                queryset = queryset.filter(date__lte=date_to)
            
            if status:
                queryset = queryset.filter(status=status)
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(staff__user__first_name__icontains=search_query) |
                Q(staff__user__last_name__icontains=search_query) |
                Q(staff__employee_id__icontains=search_query) |
                Q(remarks__icontains=search_query)
            )
        
        # Optimize query
        queryset = queryset.select_related('staff', 'staff__user', 'institution').order_by('-date', 'staff__user__first_name')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add filter form
        context['filter_form'] = getattr(self, 'filter_form', AttendanceFilterForm(request=self.request))
        
        # Add statistics
        queryset = self.get_queryset()
        context['total_records'] = queryset.count()
        
        # Calculate statistics
        context['present_count'] = queryset.filter(status='present').count()
        context['absent_count'] = queryset.filter(status='absent').count()
        context['half_day_count'] = queryset.filter(status='half_day').count()
        context['leave_count'] = queryset.filter(status='leave').count()
        
        # Calculate average hours worked (only for present days with check-in/out)
        worked_attendances = queryset.filter(status='present', check_in__isnull=False, check_out__isnull=False)
        avg_hours = worked_attendances.aggregate(Avg('hours_worked'))['hours_worked__avg'] or 0
        context['avg_hours_worked'] = round(avg_hours, 2)
        
        # Total hours worked
        total_hours = worked_attendances.aggregate(Sum('hours_worked'))['hours_worked__sum'] or 0
        context['total_hours_worked'] = round(total_hours, 2)
        
        # Date range for filter defaults
        context['default_date_from'] = self.request.GET.get('date_from', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        context['default_date_to'] = self.request.GET.get('date_to', timezone.now().strftime('%Y-%m-%d'))
        
        return context


class AttendanceCreateView( StaffManagementRequiredMixin, CreateView):
    model = HrAttendance
    form_class = AttendanceForm
    template_name = 'hr/attendance/attendance_form.html'
    success_url = reverse_lazy('hr:attendance_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        institution = get_user_institution(user)
        
        # Get today's date
        today = timezone.now().date()
        context['today'] = today
        
        # Get all active employees for the institution
        if institution:
            employees = Staff.objects.filter(
                institution=institution, 
                is_active=True
            ).select_related('user', 'department')
        else:
            employees = Staff.objects.filter(
                is_active=True
            ).select_related('user', 'department')
        
        context['staff_list'] = employees
        context['staff_count'] = employees.count()
        
        # Get unique departments for filtering
        departments = Department.objects.filter(
            staff__in=employees
        ).distinct().annotate(
            staff_count=Count('staff')
        )
        context['departments'] = departments
        
        # Check if date and department are provided in GET parameters
        selected_date = self.request.GET.get('date', today.isoformat())
        selected_department_id = self.request.GET.get('department_id')
        
        context['selected_date'] = selected_date
        context['selected_department_id'] = selected_department_id
        
        # Filter employees by department if specified
        if selected_department_id:
            filtered_employees = employees.filter(department_id=selected_department_id)
            context['filtered_staff_list'] = filtered_employees
        else:
            context['filtered_staff_list'] = employees
        
        return context
    
    def form_valid(self, form):
        user = self.request.user
        institution = get_user_institution(user)
        
        if institution:
            form.instance.institution = institution
        
        # Handle multiple attendance records
        if 'bulk_submit' in self.request.POST:
            return self.handle_bulk_submission(self.request)
        else:
            messages.success(self.request, "Attendance record created successfully.")
            return super().form_valid(form)
    
    def post(self, request, *args, **kwargs):
        """Override post to handle both single and bulk attendance"""
        if 'bulk_submit' in request.POST:
            return self.handle_bulk_submission(request)
        return super().post(request, *args, **kwargs)
    
    def handle_bulk_submission(self, request):
        """Handle bulk attendance submission from the grid interface"""
        try:
            date_str = request.POST.get('attendance_date')
            if not date_str:
                messages.error(request, "Date is required.")
                return redirect('hr:attendance_create')
            
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            user = request.user
            institution = get_user_institution(user)
            created_count = 0
            updated_count = 0
            
            # Extract attendance data from the form
            for key, value in request.POST.items():
                if key.startswith('staff_'):
                    staff_id = key.replace('staff_', '')
                    status = value
                    
                    if status in ['present', 'absent', 'half_day', 'leave', 'holiday', 'weekend']:
                        try:
                            staff = Staff.objects.get(id=staff_id, institution=institution)
                            
                            # Check if attendance already exists for this date and staff
                            existing_attendance = HrAttendance.objects.filter(
                                staff=staff,
                                date=date,
                                institution=institution
                            ).first()
                            
                            if existing_attendance:
                                # Update existing record
                                existing_attendance.status = status
                                existing_attendance.save()
                                updated_count += 1
                            else:
                                # Create new attendance record
                                attendance = HrAttendance(
                                    staff=staff,
                                    date=date,
                                    status=status,
                                    institution=institution
                                )
                                attendance.save()
                                created_count += 1
                                
                        except Staff.DoesNotExist:
                            messages.warning(request, f"Staff with ID {staff_id} not found.")
                        except Exception as e:
                            messages.error(request, f"Error processing attendance for staff {staff_id}: {str(e)}")
            
            # Prepare success message
            if created_count > 0 and updated_count > 0:
                messages.success(request, f"Successfully created {created_count} and updated {updated_count} attendance records.")
            elif created_count > 0:
                messages.success(request, f"Successfully created {created_count} attendance records.")
            elif updated_count > 0:
                messages.success(request, f"Successfully updated {updated_count} attendance records.")
            else:
                messages.info(request, "No attendance records were processed.")
            
            return redirect(self.success_url)
            
        except Exception as e:
            messages.error(request, f"Error processing attendance records: {str(e)}")
            return redirect('hr:attendance_create')

class AttendanceDetailView( StaffManagementRequiredMixin, DetailView):
    model = HrAttendance
    template_name = 'hr/attendance/attendance_detail.html'
    context_object_name = 'attendance'

class AttendanceUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = HrAttendance
    form_class = AttendanceForm
    template_name = 'hr/attendance/attendance_form.html'
    success_url = reverse_lazy('hr:attendance_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, "Attendance record updated successfully.")
        return super().form_valid(form)

class AttendanceDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = HrAttendance
    template_name = 'hr/attendance/attendance_confirm_delete.html'
    success_url = reverse_lazy('hr:attendance_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attendance = self.get_object()
        context['attendance'] = attendance
        context['organization'] = get_user_institution(self.request.user)
        context['title'] = "Delete Attendance Record"
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Attendance record deleted successfully.")
        return super().delete(request, *args, **kwargs)

class AttendanceExportView( StaffManagementRequiredMixin, ListView):
    model = HrAttendance
    context_object_name = 'attendances'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return HrAttendance.objects.filter(institution=institution).select_related('staff', 'staff__user')
    
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        queryset = self.get_queryset()
        
        # Apply filters from request
        form = AttendanceFilterForm(request.GET, request=request)
        if form.is_valid():
            staff = form.cleaned_data.get('staff')
            date_from = form.cleaned_data.get('date_from')
            date_to = form.cleaned_data.get('date_to')
            status = form.cleaned_data.get('status')
            
            if staff:
                queryset = queryset.filter(staff=staff)
            
            if date_from:
                queryset = queryset.filter(date__gte=date_from)
            
            if date_to:
                queryset = queryset.filter(date__lte=date_to)
            
            if status:
                queryset = queryset.filter(status=status)
        
        # Build filename
        filename = f"attendance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Build data rows
        rows = []
        for attendance in queryset:
            rows.append({
                "employee_id": attendance.staff.employee_id,
                "staff_name": attendance.staff.user.get_full_name(),
                "date": attendance.date.strftime('%Y-%m-%d'),
                "day": attendance.date.strftime('%A'),
                "check_in": attendance.check_in.strftime('%H:%M') if attendance.check_in else 'N/A',
                "check_out": attendance.check_out.strftime('%H:%M') if attendance.check_out else 'N/A',
                "status": attendance.get_status_display(),
                "hours_worked": float(attendance.hours_worked),
                "remarks": attendance.remarks,
                "created_at": attendance.created_at.strftime('%Y-%m-%d %H:%M'),
                "updated_at": attendance.updated_at.strftime('%Y-%m-%d %H:%M'),
            })

        # Get organization info
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
        """Export data to CSV format"""
        buffer = StringIO()
        writer = csv.writer(buffer)
        
        # Write header
        writer.writerow([
            'Employee ID', 'Staff Name', 'Date', 'Day', 'Check In',
            'Check Out', 'Status', 'Hours Worked', 'Remarks',
            'Created At', 'Updated At'
        ])
        
        # Write data rows
        for row in rows:
            writer.writerow([
                row['employee_id'],
                row['staff_name'],
                row['date'],
                row['day'],
                row['check_in'],
                row['check_out'],
                row['status'],
                row['hours_worked'],
                row['remarks'],
                row['created_at'],
                row['updated_at'],
            ])
        
        # Add summary row
        writer.writerow([])
        writer.writerow(['Total Records:', len(rows)])
        
        # Calculate totals
        total_hours = sum(row['hours_worked'] for row in rows)
        present_count = len([r for r in rows if 'Present' in r['status']])
        absent_count = len([r for r in rows if 'Absent' in r['status']])
        
        writer.writerow(['Total Hours Worked:', round(total_hours, 2)])
        writer.writerow(['Present Count:', present_count])
        writer.writerow(['Absent Count:', absent_count])
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    def export_excel(self, rows, filename, organization):
        """Export data to Excel format"""
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Attendance')
            
            # Add formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#3b5998',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True
            })
            
            number_format = workbook.add_format({'num_format': '#,##0.00'})
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            time_format = workbook.add_format({'num_format': 'hh:mm'})
            datetime_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm'})
            center_format = workbook.add_format({'align': 'center'})
            
            # Write headers
            headers = [
                'Employee ID', 'Staff Name', 'Date', 'Day', 'Check In',
                'Check Out', 'Status', 'Hours Worked', 'Remarks',
                'Created At', 'Updated At'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Write data
            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data['employee_id'])
                worksheet.write(row_idx, 1, row_data['staff_name'])
                worksheet.write(row_idx, 2, row_data['date'], date_format)
                worksheet.write(row_idx, 3, row_data['day'], center_format)
                worksheet.write(row_idx, 4, row_data['check_in'] if row_data['check_in'] != 'N/A' else '', time_format)
                worksheet.write(row_idx, 5, row_data['check_out'] if row_data['check_out'] != 'N/A' else '', time_format)
                worksheet.write(row_idx, 6, row_data['status'])
                worksheet.write(row_idx, 7, float(row_data['hours_worked']), number_format)
                worksheet.write(row_idx, 8, row_data['remarks'])
                worksheet.write(row_idx, 9, row_data['created_at'], datetime_format)
                worksheet.write(row_idx, 10, row_data['updated_at'], datetime_format)
            
            # Adjust column widths
            worksheet.set_column('A:A', 15)  # Employee ID
            worksheet.set_column('B:B', 25)  # Staff Name
            worksheet.set_column('C:C', 12)  # Date
            worksheet.set_column('D:D', 10)  # Day
            worksheet.set_column('E:F', 10)  # Check In/Out
            worksheet.set_column('G:G', 15)  # Status
            worksheet.set_column('H:H', 12)  # Hours Worked
            worksheet.set_column('I:I', 30)  # Remarks
            worksheet.set_column('J:K', 18)  # Date columns
            
            # Add summary
            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, 'Total Records:')
            worksheet.write(summary_row, 1, len(rows))
            
            # Calculate totals
            total_hours = sum(float(row['hours_worked']) for row in rows)
            present_count = len([r for r in rows if 'Present' in r['status']])
            absent_count = len([r for r in rows if 'Absent' in r['status']])
            
            summary_row += 1
            worksheet.write(summary_row, 0, 'Total Hours Worked:')
            worksheet.write(summary_row, 1, total_hours, number_format)
            
            summary_row += 1
            worksheet.write(summary_row, 0, 'Present Count:')
            worksheet.write(summary_row, 1, present_count)
            
            summary_row += 1
            worksheet.write(summary_row, 0, 'Absent Count:')
            worksheet.write(summary_row, 1, absent_count)
            
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
        """Export data to PDF format"""
        # Calculate totals for summary
        total_hours = sum(float(row['hours_worked']) for row in rows)
        present_count = len([r for r in rows if 'Present' in r['status']])
        absent_count = len([r for r in rows if 'Absent' in r['status']])
        
        context = {
            "attendances": rows,
            "total_count": total_count,
            "total_hours": round(total_hours, 2),
            "present_count": present_count,
            "absent_count": absent_count,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Attendance Export",
            "columns": [
                {'name': 'Employee ID', 'width': '12%'},
                {'name': 'Staff Name', 'width': '18%'},
                {'name': 'Date', 'width': '10%'},
                {'name': 'Check In', 'width': '8%'},
                {'name': 'Check Out', 'width': '8%'},
                {'name': 'Status', 'width': '10%'},
                {'name': 'Hours', 'width': '8%'},
                {'name': 'Remarks', 'width': '18%'},
            ]
        }
        
        pdf_bytes = render_to_pdf("hr/export/attendance_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

class AttendanceDetailExportView( StaffManagementRequiredMixin, View):
    """Export a single attendance record's details in CSV, Excel, or PDF."""

    def get(self, request, pk, *args, **kwargs):
        attendance = get_object_or_404(HrAttendance, pk=pk)
        format_type = request.GET.get('format', 'csv').lower()

        # Prepare data row with all fields
        row = {
            "employee_id": attendance.staff.employee_id,
            "staff_name": attendance.staff.user.get_full_name(),
            "staff_department": attendance.staff.department.name if attendance.staff.department else 'N/A',
            "staff_designation": attendance.staff.designation.name if attendance.staff.designation else 'N/A',
            "date": attendance.date.strftime('%Y-%m-%d'),
            "day": attendance.date.strftime('%A'),
            "check_in": attendance.check_in.strftime('%H:%M') if attendance.check_in else 'N/A',
            "check_out": attendance.check_out.strftime('%H:%M') if attendance.check_out else 'N/A',
            "status": attendance.get_status_display(),
            "hours_worked": float(attendance.hours_worked),
            "remarks": attendance.remarks,
            "created_at": attendance.created_at.strftime('%Y-%m-%d %H:%M'),
            "updated_at": attendance.updated_at.strftime('%Y-%m-%d %H:%M'),
        }

        organization = get_user_institution(request.user)
        filename = f"attendance_{attendance.staff.employee_id}_{attendance.date}"

        if format_type == 'csv':
            return self.export_csv(row, filename, organization)
        elif format_type == 'excel':
            return self.export_excel(row, filename, organization)
        elif format_type == 'pdf':
            return self.export_pdf(row, filename, attendance, organization)
        else:
            return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, row, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        # Header
        writer.writerow(['Field', 'Value'])

        # Data
        fields = [
            ('Employee ID', row['employee_id']),
            ('Staff Name', row['staff_name']),
            ('Department', row['staff_department']),
            ('Designation', row['staff_designation']),
            ('Date', row['date']),
            ('Day', row['day']),
            ('Check In', row['check_in']),
            ('Check Out', row['check_out']),
            ('Status', row['status']),
            ('Hours Worked', row['hours_worked']),
            ('Remarks', row['remarks']),
            ('Created At', row['created_at']),
            ('Updated At', row['updated_at']),
        ]

        for field, value in fields:
            writer.writerow([field, value])

        # Summary
        writer.writerow([])
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])

        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, row, filename, organization):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Attendance Detail')

            header_format = workbook.add_format({
                'bold': True, 
                'bg_color': '#3b5998', 
                'font_color': 'white', 
                'border': 1,
                'text_wrap': True
            })
            number_format = workbook.add_format({'num_format': '#,##0.00'})
            bold_format = workbook.add_format({'bold': True})

            # Write headers
            worksheet.write(0, 0, 'Field', header_format)
            worksheet.write(0, 1, 'Value', header_format)

            # Data rows
            fields = [
                ('Employee ID', row['employee_id']),
                ('Staff Name', row['staff_name']),
                ('Department', row['staff_department']),
                ('Designation', row['staff_designation']),
                ('Date', row['date']),
                ('Day', row['day']),
                ('Check In', row['check_in']),
                ('Check Out', row['check_out']),
                ('Status', row['status']),
                ('Hours Worked', row['hours_worked']),
                ('Remarks', row['remarks']),
                ('Created At', row['created_at']),
                ('Updated At', row['updated_at']),
            ]

            for row_idx, (field, value) in enumerate(fields, start=1):
                worksheet.write(row_idx, 0, field, bold_format)
                
                if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '').isdigit()):
                    worksheet.write(row_idx, 1, float(value), number_format)
                else:
                    worksheet.write(row_idx, 1, value)

            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:B', 30)

            # Summary
            summary_row = len(fields) + 2
            worksheet.write(summary_row, 0, 'Organization:', bold_format)
            worksheet.write(summary_row, 1, organization.name if organization else 'N/A')
            worksheet.write(summary_row + 1, 0, 'Export Date:', bold_format)
            worksheet.write(summary_row + 1, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, row, filename, attendance, organization):
        context = {
            "attendance": row,
            "original_attendance": attendance,
            "organization": organization,
            "export_date": timezone.now(),
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": f"Attendance - {row['employee_id']}",
        }
        
        pdf_bytes = render_to_pdf("hr/export/attendance_detail_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)