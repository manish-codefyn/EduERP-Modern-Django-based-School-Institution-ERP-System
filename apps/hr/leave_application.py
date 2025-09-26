from datetime import datetime, timedelta
from io import BytesIO, StringIO
import csv
import xlsxwriter

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View

from apps.core.mixins import StaffManagementRequiredMixin, DirectorRequiredMixin, StaffRequiredMixin
from apps.core.utils import get_user_institution
from utils.utils import render_to_pdf, export_pdf_response, qr_generate

from .models import LeaveApplication, LeaveType
from .forms import LeaveApplicationForm, LeaveApplicationReviewForm


class LeaveApplicationExportView( DirectorRequiredMixin, ListView):
    model = LeaveApplication
    context_object_name = 'leave_applications'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return LeaveApplication.objects.filter(institution=institution)
    
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        queryset = self.get_queryset()
        
        # Apply filters from request
        status = request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        leave_type = request.GET.get('leave_type')
        if leave_type:
            queryset = queryset.filter(leave_type_id=leave_type)
        
        date_from = request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(end_date__gte=date_from)
        
        date_to = request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(start_date__lte=date_to)
        
        # Build filename
        filename = f"leave_applications_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Build data rows
        rows = []
        for application in queryset:
            rows.append({
                "employee_id": application.staff.employee_id,
                "staff_name": application.staff.user.get_full_name(),
                "leave_type": application.leave_type.name,
                "leave_code": application.leave_type.code,
                "start_date": application.start_date.strftime('%Y-%m-%d'),
                "end_date": application.end_date.strftime('%Y-%m-%d'),
                "total_days": application.total_days,
                "reason": application.reason,
                "status": application.get_status_display(),
                "applied_date": application.created_at.strftime('%Y-%m-%d %H:%M'),
                "approved_by": application.approved_by.get_full_name() if application.approved_by else '',
                "approved_date": application.approved_date.strftime('%Y-%m-%d %H:%M') if application.approved_date else '',
                "remarks": application.remarks,
                "has_document": "Yes" if application.supporting_document else "No"
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
            'Employee ID', 'Staff Name', 'Leave Type', 'Leave Code', 'Start Date',
            'End Date', 'Total Days', 'Reason', 'Status', 'Applied Date',
            'Approved By', 'Approved Date', 'Remarks', 'Has Document'
        ])
        
        # Write data rows
        for row in rows:
            writer.writerow([
                row['employee_id'],
                row['staff_name'],
                row['leave_type'],
                row['leave_code'],
                row['start_date'],
                row['end_date'],
                row['total_days'],
                row['reason'][:100] + '...' if len(row['reason']) > 100 else row['reason'],  # Truncate long reasons
                row['status'],
                row['applied_date'],
                row['approved_by'],
                row['approved_date'],
                row['remarks'][:100] + '...' if row['remarks'] and len(row['remarks']) > 100 else row['remarks'],
                row['has_document']
            ])
        
        # Add summary row
        writer.writerow([])
        writer.writerow(['Total Applications:', len(rows)])
        
        # Count by status
        status_counts = {}
        for row in rows:
            status_counts[row['status']] = status_counts.get(row['status'], 0) + 1
        
        for status, count in status_counts.items():
            writer.writerow([f'{status} Applications:', count])
        
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    def export_excel(self, rows, filename, organization):
        """Export data to Excel format"""
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Leave Applications')
            
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
            
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            datetime_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm'})
            center_format = workbook.add_format({'align': 'center'})
            
            # Write headers
            headers = [
                'Employee ID', 'Staff Name', 'Leave Type', 'Leave Code', 'Start Date',
                'End Date', 'Total Days', 'Reason', 'Status', 'Applied Date',
                'Approved By', 'Approved Date', 'Remarks', 'Has Document'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Write data
            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data['employee_id'])
                worksheet.write(row_idx, 1, row_data['staff_name'])
                worksheet.write(row_idx, 2, row_data['leave_type'])
                worksheet.write(row_idx, 3, row_data['leave_code'])
                worksheet.write(row_idx, 4, row_data['start_date'], date_format)
                worksheet.write(row_idx, 5, row_data['end_date'], date_format)
                worksheet.write(row_idx, 6, row_data['total_days'], center_format)
                worksheet.write(row_idx, 7, row_data['reason'])
                worksheet.write(row_idx, 8, row_data['status'], center_format)
                worksheet.write(row_idx, 9, row_data['applied_date'], datetime_format)
                worksheet.write(row_idx, 10, row_data['approved_by'])
                worksheet.write(row_idx, 11, row_data['approved_date'], datetime_format)
                worksheet.write(row_idx, 12, row_data['remarks'] or '')
                worksheet.write(row_idx, 13, row_data['has_document'], center_format)
            
            # Adjust column widths
            worksheet.set_column('A:A', 15)  # Employee ID
            worksheet.set_column('B:B', 25)  # Staff Name
            worksheet.set_column('C:C', 20)  # Leave Type
            worksheet.set_column('D:D', 15)  # Leave Code
            worksheet.set_column('E:F', 12)  # Dates
            worksheet.set_column('G:G', 12)  # Total Days
            worksheet.set_column('H:H', 40)  # Reason
            worksheet.set_column('I:I', 15)  # Status
            worksheet.set_column('J:J', 18)  # Applied Date
            worksheet.set_column('K:K', 20)  # Approved By
            worksheet.set_column('L:L', 18)  # Approved Date
            worksheet.set_column('M:M', 30)  # Remarks
            worksheet.set_column('N:N', 12)  # Has Document
            
            # Add summary
            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, 'Total Applications:')
            worksheet.write(summary_row, 1, len(rows))
            
            # Count by status
            status_counts = {}
            for row in rows:
                status_counts[row['status']] = status_counts.get(row['status'], 0) + 1
            
            summary_row += 1
            for status, count in status_counts.items():
                worksheet.write(summary_row, 0, f'{status} Applications:')
                worksheet.write(summary_row, 1, count)
                summary_row += 1
            
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
    
    def export_pdf(self, rows, filename, organization, total_count):
        """Export data to PDF format"""
        # Count by status for summary
        status_counts = {}
        for row in rows:
            status_counts[row['status']] = status_counts.get(row['status'], 0) + 1
        
        context = {
            "applications": rows,
            "total_count": total_count,
            "status_counts": status_counts,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Leave Applications Export",
            "columns": [
                {'name': 'Employee ID', 'width': '12%'},
                {'name': 'Staff Name', 'width': '18%'},
                {'name': 'Leave Type', 'width': '15%'},
                {'name': 'Period', 'width': '15%'},
                {'name': 'Days', 'width': '8%'},
                {'name': 'Status', 'width': '12%'},
                {'name': 'Applied On', 'width': '15%'},
            ]
        }
        
        pdf_bytes = render_to_pdf("hr/export/leave_applications_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)


class LeaveApplicationDetailExportView( DirectorRequiredMixin, View):
    """Export a single leave application's details in CSV, Excel, or PDF."""

    def get(self, request, pk, *args, **kwargs):
        application = get_object_or_404(LeaveApplication, pk=pk)
        format_type = request.GET.get('format', 'csv').lower()

        # Prepare data row with all fields
        row = {
            # Application Information
            "application_id": str(application.id),
            "employee_id": application.staff.employee_id,
            "staff_name": application.staff.user.get_full_name(),
            "staff_department": application.staff.department.name if application.staff.department else 'N/A',
            "staff_designation": application.staff.designation.name if application.staff.designation else 'N/A',
            
            # Leave Details
            "leave_type": application.leave_type.name,
            "leave_code": application.leave_type.code,
            "max_days_allowed": application.leave_type.max_days,
            "carry_forward": "Yes" if application.leave_type.carry_forward else "No",
            "max_carry_forward": application.leave_type.max_carry_forward or 'N/A',
            "requires_approval": "Yes" if application.leave_type.requires_approval else "No",
            
            # Application Period
            "start_date": application.start_date.strftime('%Y-%m-%d'),
            "end_date": application.end_date.strftime('%Y-%m-%d'),
            "total_days": application.total_days,
            "reason": application.reason,
            
            # Status and Approval
            "status": application.get_status_display(),
            "applied_date": application.created_at.strftime('%Y-%m-%d %H:%M'),
            "approved_by": application.approved_by.get_full_name() if application.approved_by else 'N/A',
            "approved_date": application.approved_date.strftime('%Y-%m-%d %H:%M') if application.approved_date else 'N/A',
            "remarks": application.remarks or 'N/A',
            
            # Document Info
            "has_supporting_document": "Yes" if application.supporting_document else "No",
            "document_name": application.supporting_document.name.split('/')[-1] if application.supporting_document else 'N/A',
            
            # Additional Metadata
            "last_updated": application.updated_at.strftime('%Y-%m-%d %H:%M')
        }

        organization = get_user_institution(request.user)
        filename = f"leave_application_{application.staff.employee_id}_{application.start_date.strftime('%Y%m%d')}"

        # Generate QR code for quick reference
        qr_data = f"Leave Application: {application.staff.employee_id} - {application.leave_type.name} - {application.start_date} to {application.end_date}"
        qr_code_img = qr_generate(qr_data)

        if format_type == 'csv':
            return self.export_csv(row, filename, organization)
        elif format_type == 'excel':
            return self.export_excel(row, filename, organization)
        elif format_type == 'pdf':
            return self.export_pdf(row, filename, application, organization, qr_code_img)
        else:
            return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, row, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        # Header
        writer.writerow([
            'Application ID', 'Employee ID', 'Staff Name', 'Department', 'Designation',
            'Leave Type', 'Leave Code', 'Max Days Allowed', 'Carry Forward', 'Max Carry Forward',
            'Requires Approval', 'Start Date', 'End Date', 'Total Days', 'Reason',
            'Status', 'Applied Date', 'Approved By', 'Approved Date', 'Remarks',
            'Has Supporting Document', 'Document Name', 'Last Updated'
        ])

        # Data
        writer.writerow([
            row['application_id'], row['employee_id'], row['staff_name'], 
            row['staff_department'], row['staff_designation'], row['leave_type'],
            row['leave_code'], row['max_days_allowed'], row['carry_forward'],
            row['max_carry_forward'], row['requires_approval'], row['start_date'],
            row['end_date'], row['total_days'], row['reason'], row['status'],
            row['applied_date'], row['approved_by'], row['approved_date'],
            row['remarks'], row['has_supporting_document'], row['document_name'],
            row['last_updated']
        ])

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
            worksheet = workbook.add_worksheet('Leave Application Detail')

            header_format = workbook.add_format({
                'bold': True, 
                'bg_color': '#3b5998', 
                'font_color': 'white', 
                'border': 1,
                'text_wrap': True
            })
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            datetime_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm'})
            center_format = workbook.add_format({'align': 'center'})

            headers = [
                'Application ID', 'Employee ID', 'Staff Name', 'Department', 'Designation',
                'Leave Type', 'Leave Code', 'Max Days Allowed', 'Carry Forward', 'Max Carry Forward',
                'Requires Approval', 'Start Date', 'End Date', 'Total Days', 'Reason',
                'Status', 'Applied Date', 'Approved By', 'Approved Date', 'Remarks',
                'Has Supporting Document', 'Document Name', 'Last Updated'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            data = [
                row['application_id'], row['employee_id'], row['staff_name'], 
                row['staff_department'], row['staff_designation'], row['leave_type'],
                row['leave_code'], row['max_days_allowed'], row['carry_forward'],
                row['max_carry_forward'], row['requires_approval'], row['start_date'],
                row['end_date'], row['total_days'], row['reason'], row['status'],
                row['applied_date'], row['approved_by'], row['approved_date'],
                row['remarks'], row['has_supporting_document'], row['document_name'],
                row['last_updated']
            ]
            
            for col, value in enumerate(data):
                fmt = None
                if col in [11, 12]:  # Date fields
                    fmt = date_format
                elif col in [16, 18, 22]:  # DateTime fields
                    fmt = datetime_format
                elif col in [7, 8, 9, 13, 20]:  # Numeric and boolean fields
                    fmt = center_format
                worksheet.write(1, col, value, fmt)

            worksheet.set_column('A:W', 18)

            # Summary
            worksheet.write(3, 0, 'Organization:')
            worksheet.write(3, 1, organization.name if organization else 'N/A')
            worksheet.write(4, 0, 'Export Date:')
            worksheet.write(4, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, row, filename, application, organization, qr_code_img):
        context = {
            "application": row,
            "original_application": application,
            "organization": organization,
            "export_date": timezone.now(),
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": f"Leave Application - {row['employee_id']}",
            "qr_code": qr_code_img,
            "supporting_document_url": application.supporting_document.url if application.supporting_document else None
        }
        
        pdf_bytes = render_to_pdf("hr/export/leave_application_detail_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)


class LeaveApplicationListView( DirectorRequiredMixin, ListView):
    model = LeaveApplication
    template_name = 'hr/leave_application/leave_application_list.html'
    context_object_name = 'leave_applications'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter by user's institution
        institution = get_user_institution(user)
        if institution:
            queryset = queryset.filter(institution=institution)
        
        # For staff users, show only their own applications
        if hasattr(user, 'staff'):
            queryset = queryset.filter(staff=user.staff)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by leave type
        leave_type = self.request.GET.get('leave_type')
        if leave_type:
            queryset = queryset.filter(leave_type_id=leave_type)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(end_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(start_date__lte=date_to)
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(staff__user__first_name__icontains=search_query) |
                Q(staff__user__last_name__icontains=search_query) |
                Q(leave_type__name__icontains=search_query) |
                Q(reason__icontains=search_query)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add filter options
        context['status_choices'] = dict(LeaveApplication.STATUS_CHOICES)
        
        # Add leave types for filter dropdown
        institution = get_user_institution(user)
        if institution:
            context['leave_types'] = LeaveType.objects.filter(institution=institution, is_active=True)
        
        # Add statistics
        queryset = self.get_queryset()
        context['total_applications'] = queryset.count()
        context['pending_count'] = queryset.filter(status='pending').count()
        context['approved_count'] = queryset.filter(status='approved').count()
        context['rejected_count'] = queryset.filter(status='rejected').count()
        
        # Check if user can review applications
        context['can_review'] = user.is_superadmin or user.is_institution_admin or user.is_principal
        
        return context

class LeaveApplicationCreateView(StaffRequiredMixin, CreateView):
    model = LeaveApplication
    form_class = LeaveApplicationForm
    template_name = 'hr/leave_application/leave_application_form.html'
    success_url = reverse_lazy('hr:leave_application_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        user = self.request.user

        # Ensure the user has a linked staff profile
        if not hasattr(user, 'staff_profile'):
            messages.error(self.request, "Only staff members can apply for leave.")
            return redirect(self.success_url)

        staff_profile = user.staff_profile
        form.instance.staff = staff_profile
        form.instance.institution = staff_profile.institution

        # Calculate total leave days
        total_days = (form.instance.end_date - form.instance.start_date).days + 1

        # TODO: Implement leave balance validation logic here
        # Example:
        # if total_days > staff_profile.get_leave_balance(leave_type):
        #     messages.error(self.request, "Insufficient leave balance.")
        #     return redirect(self.success_url)

        messages.success(self.request, "Leave application submitted successfully. Waiting for approval.")
        return super().form_valid(form)
    

class LeaveApplicationDetailView(DirectorRequiredMixin, DetailView):
    model = LeaveApplication
    template_name = 'hr/leave_application/leave_application_detail.html'
    context_object_name = 'application'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Staff can only see their own applications
        if hasattr(user, 'staff'):
            queryset = queryset.filter(staff=user.staff)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_review'] = self.request.user.is_superadmin or self.request.user.is_institution_admin or self.request.user.is_principal
        context['review_form'] = LeaveApplicationReviewForm(instance=self.object)
        return context

class LeaveApplicationUpdateView(DirectorRequiredMixin, UpdateView):
    model = LeaveApplication
    form_class = LeaveApplicationForm
    template_name = 'hr/leave_application/leave_application_form.html'
    success_url = reverse_lazy('hr:leave_application_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Staff can only update their own pending applications
        if hasattr(user, 'staff'):
            queryset = queryset.filter(staff=user.staff, status='pending')
        
        return queryset
    
    def form_valid(self, form):
        messages.success(self.request, "Leave application updated successfully.")
        return super().form_valid(form)

class LeaveApplicationDeleteView(DirectorRequiredMixin, DeleteView):
    model = LeaveApplication
    template_name = 'hr/leave_application/leave_application_confirm_delete.html'
    success_url = reverse_lazy('hr:leave_application_list')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Staff can only delete their own pending applications
        if hasattr(user, 'staff'):
            queryset = queryset.filter(staff=user.staff, status='pending')
        
        return queryset
    
    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, "Leave application cancelled successfully.")
        return super().delete(request, *args, **kwargs)


class LeaveApplicationReviewView(DirectorRequiredMixin, UpdateView):
    model = LeaveApplication
    form_class = LeaveApplicationReviewForm
    template_name = 'hr/leave_application/leave_application_review.html'
    
    def get_success_url(self):
        return reverse_lazy('hr:leave_application_detail', kwargs={'pk': self.object.pk})
    
    def dispatch(self, request, *args, **kwargs):
        # Only allow supervisors to review applications
        if not (request.user.is_superadmin or request.user.is_institution_admin or request.user.is_principal):
            raise PermissionDenied("You don't have permission to review leave applications.")
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        if form.instance.status in ['approved', 'rejected']:
            form.instance.approved_by = self.request.user
            form.instance.approved_date = timezone.now()
        
        messages.success(self.request, f"Leave application {form.instance.get_status_display().lower()} successfully.")
        return super().form_valid(form)


def get_leave_balance(request):
    """AJAX endpoint to get leave balance for a staff member"""
    if request.method == 'GET' and request.is_ajax():
        leave_type_id = request.GET.get('leave_type_id')
        staff_id = request.GET.get('staff_id', None)
        
        if not staff_id and hasattr(request.user, 'staff'):
            staff_id = request.user.staff.id
        
        if leave_type_id and staff_id:
            # TODO: Implement leave balance calculation
            # This is a placeholder implementation
            balance = 15  # Example balance
            return JsonResponse({'balance': balance})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)