from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from io import StringIO, BytesIO
import csv
import xlsxwriter

from apps.core.mixins import DirectorRequiredMixin
from apps.core.utils import get_user_institution
from .models import HostelAttendance
from .forms import HostelAttendanceForm
from utils.utils import render_to_pdf, export_pdf_response


class HostelAttendanceListView(DirectorRequiredMixin, ListView):
    model = HostelAttendance
    template_name = 'hostel/attendance/attendance_list.html'
    context_object_name = 'attendances'
    paginate_by = 20

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = HostelAttendance.objects.filter(
            student__institution=institution
        ).select_related('student', 'recorded_by').order_by('-date', 'student__first_name', 'student__last_name')

        # Filters
        date_filter = self.request.GET.get('date')
        student_filter = self.request.GET.get('student')
        status_filter = self.request.GET.get('status')

        if date_filter:
            queryset = queryset.filter(date=date_filter)

        if student_filter:
            queryset = queryset.filter(student_id=student_filter)

        if status_filter:
            if status_filter.lower() == 'present':
                queryset = queryset.filter(present=True)
            elif status_filter.lower() == 'absent':
                queryset = queryset.filter(present=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)

        attendances = self.get_queryset()
        today = timezone.now().date()

        # Stats
        context['total_attendances'] = attendances.count()
        context['today_attendances'] = attendances.filter(date=today).count()
        context['present_count'] = attendances.filter(present=True).count()
        context['absent_count'] = attendances.filter(present=False).count()

        today_attendance = attendances.filter(date=today)
        context['today_present'] = today_attendance.filter(present=True).count()
        context['today_absent'] = today_attendance.filter(present=False).count()

        # Students for filter dropdown
        # Only active students with hostel allocations
        context['students'] = institution.students.filter(
            hostel_allocations__is_active=True
        ).order_by('first_name', 'last_name').distinct()

        # Optional: Pass current filters to template
        context['filter_date'] = self.request.GET.get('date', '')
        context['filter_student'] = self.request.GET.get('student', '')
        context['filter_status'] = self.request.GET.get('status', '')

        return context



class HostelAttendanceCreateView(DirectorRequiredMixin, CreateView):
    model = HostelAttendance
    form_class = HostelAttendanceForm
    template_name = 'hostel/attendance/attendance_form.html'
    success_url = reverse_lazy('hostel:attendance_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['institution'] = get_user_institution(self.request.user)
        return kwargs

    def form_valid(self, form):
        form.instance.recorded_by = getattr(self.request.user, 'staff_profile', None)
        messages.success(self.request, _('Attendance record created successfully!'))
        return super().form_valid(form)



class HostelAttendanceUpdateView(DirectorRequiredMixin, UpdateView):
    model = HostelAttendance
    form_class = HostelAttendanceForm
    template_name = 'hostel/attendance/attendance_form.html'
    success_url = reverse_lazy('hostel:attendance_list')

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return HostelAttendance.objects.filter(student__institution=institution)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['institution'] = get_user_institution(self.request.user)
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _('Attendance record updated successfully!'))
        return super().form_valid(form)


class HostelAttendanceDeleteView(DirectorRequiredMixin, DeleteView):
    model = HostelAttendance
    template_name = 'hostel/attendance/attendance_confirm_delete.html'
    success_url = reverse_lazy('hostel:attendance_list')

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return HostelAttendance.objects.filter(student__institution=institution)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('Attendance record deleted successfully!'))
        return super().delete(request, *args, **kwargs)


class HostelAttendanceDetailView(DirectorRequiredMixin, DetailView):
    model = HostelAttendance
    template_name = 'hostel/attendance/attendance_detail.html'
    context_object_name = 'attendance'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return HostelAttendance.objects.filter(student__institution=institution)


class HostelAttendanceExportView( DirectorRequiredMixin, View):
    """
    Export Hostel Attendance data.
    Supports CSV, PDF, and Excel formats.
    """

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        student_id = request.GET.get("student")
        status = request.GET.get("status")  # present/absent

        # Base queryset
        institution = get_user_institution(request.user)
        qs = HostelAttendance.objects.filter(
            student__institution=institution
        ).select_related('student', 'recorded_by').order_by('-date', 'student__roll_number')

        # Apply filters
        if start_date:
            qs = qs.filter(date__gte=start_date)
        
        if end_date:
            qs = qs.filter(date__lte=end_date)
        
        if student_id:
            qs = qs.filter(student_id=student_id)
        
        if status:
            if status.lower() == "present":
                qs = qs.filter(present=True)
            elif status.lower() == "absent":
                qs = qs.filter(present=False)

        # Build filename
        filename_parts = ["hostel_attendance"]
        if start_date:
            filename_parts.append(f"from_{start_date}")
        if end_date:
            filename_parts.append(f"to_{end_date}")
        if student_id:
            filename_parts.append(f"student_{student_id}")
        if status:
            filename_parts.append(status)
        
        filename = "_".join(filename_parts).lower()

        # Build data rows
        rows = []
        for attendance in qs:
           rows.append({
            "student": attendance.student.first_name if attendance.student else "N/A",
            "student_id": attendance.student.admission_number if attendance.student else "N/A",
            "date": attendance.date.strftime("%Y-%m-%d"),
            "status": "Present" if attendance.present else "Absent",
            "notes": attendance.notes or "-",
            "recorded_by": attendance.recorded_by.user.get_full_name() if attendance.recorded_by else "N/A",
            "recorded_at": attendance.recorded_at.strftime("%Y-%m-%d %H:%M") if attendance.recorded_at else "-",
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
            'Student Name', 'Student ID', 'Date', 'Status', 
            'Notes', 'Recorded By', 'Recorded At'
        ])
        
        # Write data rows
        for row in rows:
            writer.writerow([
                row['student'],
                row['student_id'],
                row['date'],
                row['status'],
                row['notes'],
                row['recorded_by'],
                row['recorded_at']
            ])
        
        # Add summary row
        writer.writerow([])
        writer.writerow(['Total Records:', len(rows)])
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_pdf(self, rows, filename, organization, total_count):
        """Export data to PDF format"""
        context = {
            "attendances": rows,
            "total_count": total_count,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Hostel Attendance Export",
            "columns": [
                {'name': 'Student Name', 'width': '20%'},
                {'name': 'Student ID', 'width': '15%'},
                {'name': 'Date', 'width': '12%'},
                {'name': 'Status', 'width': '10%'},
                {'name': 'Notes', 'width': '23%'},
                {'name': 'Recorded By', 'width': '10%'},
            ]
        }
        
        pdf_bytes = render_to_pdf("hostel/export/attendance_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

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
                'valign': 'vcenter'
            })
            
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            center_format = workbook.add_format({'align': 'center'})
            wrap_format = workbook.add_format({'text_wrap': True})
            
            # Write headers
            headers = [
                'Student Name', 'Student ID', 'Date', 'Status', 
                'Notes', 'Recorded By', 'Recorded At'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Write data
            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data['student'])
                worksheet.write(row_idx, 1, row_data['student_id'])
                worksheet.write(row_idx, 2, row_data['date'], date_format)
                worksheet.write(row_idx, 3, row_data['status'], center_format)
                worksheet.write(row_idx, 4, row_data['notes'], wrap_format)
                worksheet.write(row_idx, 5, row_data['recorded_by'])
                worksheet.write(row_idx, 6, row_data['recorded_at'])
            
            # Adjust column widths
            worksheet.set_column('A:A', 25)  # Student Name
            worksheet.set_column('B:B', 15)  # Student ID
            worksheet.set_column('C:C', 12)  # Date
            worksheet.set_column('D:D', 10)  # Status
            worksheet.set_column('E:E', 30)  # Notes
            worksheet.set_column('F:F', 20)  # Recorded By
            worksheet.set_column('G:G', 20)  # Recorded At
            
            # Add summary
            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, 'Total Records:')
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