
import csv
import xlsxwriter
from io import BytesIO, StringIO
from django.contrib import messages
from datetime import datetime
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View

from apps.core.mixins import StaffManagementRequiredMixin, DirectorRequiredMixin, StaffRequiredMixin
from apps.core.utils import get_user_institution
from utils.utils import render_to_pdf, export_pdf_response

from .models import LeaveBalance, LeaveType, Staff
from .forms import LeaveBalanceForm

class LeaveBalanceListView( StaffManagementRequiredMixin, ListView):
    model = LeaveBalance
    template_name = 'hr/leave_balance/leave_balance_list.html'
    context_object_name = 'leave_balances'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter by user's institution
        institution = get_user_institution(user)
        if institution:
            queryset = queryset.filter(institution=institution)
        
        # Filter by staff
        staff_id = self.request.GET.get('staff')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
        # Filter by leave type
        leave_type_id = self.request.GET.get('leave_type')
        if leave_type_id:
            queryset = queryset.filter(leave_type_id=leave_type_id)
        
        # Filter by year
        year = self.request.GET.get('year')
        if year:
            queryset = queryset.filter(year=year)
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(staff__user__first_name__icontains=search_query) |
                Q(staff__user__last_name__icontains=search_query) |
                Q(leave_type__name__icontains=search_query) |
                Q(staff__employee_id__icontains=search_query)
            )
        
        return queryset.select_related('staff', 'staff__user', 'leave_type').order_by('-year', 'staff__user__first_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add filter options
        institution = get_user_institution(user)
        if institution:
            context['staff_members'] = Staff.objects.filter(institution=institution, is_active=True)
            context['leave_types'] = LeaveType.objects.filter(institution=institution, is_active=True)
        
        # Get unique years for filter dropdown
        context['years'] = LeaveBalance.objects.filter(
            institution=institution
        ).values_list('year', flat=True).distinct().order_by('-year')
        
        # Add statistics
        queryset = self.get_queryset()
        context['total_records'] = queryset.count()
        
        # Calculate total balances
        total_allocated = queryset.aggregate(Sum('total_allocated'))['total_allocated__sum'] or 0
        total_used = queryset.aggregate(Sum('total_used'))['total_used__sum'] or 0
        total_carry_forward = queryset.aggregate(Sum('carry_forward'))['carry_forward__sum'] or 0
        total_balance = total_allocated + total_carry_forward - total_used
        
        context['total_allocated'] = total_allocated
        context['total_used'] = total_used
        context['total_carry_forward'] = total_carry_forward
        context['total_balance'] = total_balance
        
        return context

class LeaveBalanceCreateView( StaffManagementRequiredMixin, CreateView):
    model = LeaveBalance
    form_class = LeaveBalanceForm
    template_name = 'hr/leave_balance/leave_balance_form.html'
    success_url = reverse_lazy('hr:leave_balance_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        user = self.request.user
        institution = get_user_institution(user)
        
        if institution:
            form.instance.institution = institution
        
        messages.success(self.request, "Leave balance record created successfully.")
        return super().form_valid(form)

class LeaveBalanceDetailView( StaffManagementRequiredMixin, DetailView):
    model = LeaveBalance
    template_name = 'hr/leave_balance/leave_balance_detail.html'
    context_object_name = 'leave_balance'

class LeaveBalanceUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = LeaveBalance
    form_class = LeaveBalanceForm
    template_name = 'hr/leave_balance/leave_balance_form.html'
    success_url = reverse_lazy('hr:leave_balance_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, "Leave balance record updated successfully.")
        return super().form_valid(form)

class LeaveBalanceDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = LeaveBalance
    template_name = 'hr/leave_balance/leave_balance_confirm_delete.html'
    success_url = reverse_lazy('hr:leave_balance_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Current leave balance record
        leave_balance = self.get_object()
        context['leave_balance'] = leave_balance
        # Institution / organization
        context['organization'] = get_user_institution(self.request.user)
        # For header display
        context['title'] = "Delete Leave Balance"
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Leave balance record deleted successfully.")
        return super().delete(request, *args, **kwargs)


class LeaveBalanceExportView( StaffManagementRequiredMixin, ListView):
    model = LeaveBalance
    context_object_name = 'leave_balances'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return LeaveBalance.objects.filter(institution=institution).select_related('staff', 'staff__user', 'leave_type')
    
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        queryset = self.get_queryset()
        
        # Apply filters from request
        staff_id = request.GET.get('staff')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
        leave_type_id = request.GET.get('leave_type')
        if leave_type_id:
            queryset = queryset.filter(leave_type_id=leave_type_id)
        
        year = request.GET.get('year')
        if year:
            queryset = queryset.filter(year=year)
        
        # Build filename
        filename = f"leave_balances_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Build data rows
        rows = []
        for balance in queryset:
            rows.append({
                "employee_id": balance.staff.employee_id,
                "staff_name": balance.staff.user.get_full_name(),
                "leave_type": balance.leave_type.name,
                "year": balance.year,
                "total_allocated": balance.total_allocated,
                "total_used": balance.total_used,
                "carry_forward": balance.carry_forward,
                "balance": balance.balance,
                "created_at": balance.created_at.strftime('%Y-%m-%d %H:%M'),
                "updated_at": balance.updated_at.strftime('%Y-%m-%d %H:%M'),
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
            'Employee ID', 'Staff Name', 'Leave Type', 'Year', 'Total Allocated',
            'Total Used', 'Carry Forward', 'Balance', 'Created At', 'Updated At'
        ])
        
        # Write data rows
        for row in rows:
            writer.writerow([
                row['employee_id'],
                row['staff_name'],
                row['leave_type'],
                row['year'],
                row['total_allocated'],
                row['total_used'],
                row['carry_forward'],
                row['balance'],
                row['created_at'],
                row['updated_at'],
            ])
        
        # Add summary row
        writer.writerow([])
        writer.writerow(['Total Records:', len(rows)])
        
        # Calculate totals
        total_allocated = sum(row['total_allocated'] for row in rows)
        total_used = sum(row['total_used'] for row in rows)
        total_carry_forward = sum(row['carry_forward'] for row in rows)
        total_balance = sum(row['balance'] for row in rows)
        
        writer.writerow(['Total Allocated:', total_allocated])
        writer.writerow(['Total Used:', total_used])
        writer.writerow(['Total Carry Forward:', total_carry_forward])
        writer.writerow(['Total Balance:', total_balance])
        
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    def export_excel(self, rows, filename, organization):
        """Export data to Excel format"""
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Leave Balances')
            
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
            
            number_format = workbook.add_format({'num_format': '#,##0'})
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm'})
            center_format = workbook.add_format({'align': 'center'})
            
            # Write headers
            headers = [
                'Employee ID', 'Staff Name', 'Leave Type', 'Year', 'Total Allocated',
                'Total Used', 'Carry Forward', 'Balance', 'Created At', 'Updated At'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Write data
            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data['employee_id'])
                worksheet.write(row_idx, 1, row_data['staff_name'])
                worksheet.write(row_idx, 2, row_data['leave_type'])
                worksheet.write(row_idx, 3, row_data['year'], center_format)
                worksheet.write(row_idx, 4, row_data['total_allocated'], number_format)
                worksheet.write(row_idx, 5, row_data['total_used'], number_format)
                worksheet.write(row_idx, 6, row_data['carry_forward'], number_format)
                worksheet.write(row_idx, 7, row_data['balance'], number_format)
                worksheet.write(row_idx, 8, row_data['created_at'], date_format)
                worksheet.write(row_idx, 9, row_data['updated_at'], date_format)
            
            # Adjust column widths
            worksheet.set_column('A:A', 15)  # Employee ID
            worksheet.set_column('B:B', 25)  # Staff Name
            worksheet.set_column('C:C', 20)  # Leave Type
            worksheet.set_column('D:D', 8)   # Year
            worksheet.set_column('E:H', 15)  # Numeric columns
            worksheet.set_column('I:J', 18)  # Date columns
            
            # Add summary
            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, 'Total Records:')
            worksheet.write(summary_row, 1, len(rows))
            
            # Calculate totals
            total_allocated = sum(row['total_allocated'] for row in rows)
            total_used = sum(row['total_used'] for row in rows)
            total_carry_forward = sum(row['carry_forward'] for row in rows)
            total_balance = sum(row['balance'] for row in rows)
            
            summary_row += 1
            worksheet.write(summary_row, 0, 'Total Allocated:')
            worksheet.write(summary_row, 1, total_allocated, number_format)
            
            summary_row += 1
            worksheet.write(summary_row, 0, 'Total Used:')
            worksheet.write(summary_row, 1, total_used, number_format)
            
            summary_row += 1
            worksheet.write(summary_row, 0, 'Total Carry Forward:')
            worksheet.write(summary_row, 1, total_carry_forward, number_format)
            
            summary_row += 1
            worksheet.write(summary_row, 0, 'Total Balance:')
            worksheet.write(summary_row, 1, total_balance, number_format)
            
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
        total_allocated = sum(row['total_allocated'] for row in rows)
        total_used = sum(row['total_used'] for row in rows)
        total_carry_forward = sum(row['carry_forward'] for row in rows)
        total_balance = sum(row['balance'] for row in rows)
        
        context = {
            "balances": rows,
            "total_count": total_count,
            "total_allocated": total_allocated,
            "total_used": total_used,
            "total_carry_forward": total_carry_forward,
            "total_balance": total_balance,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Leave Balances Export",
            "columns": [
                {'name': 'Employee ID', 'width': '12%'},
                {'name': 'Staff Name', 'width': '18%'},
                {'name': 'Leave Type', 'width': '15%'},
                {'name': 'Year', 'width': '8%'},
                {'name': 'Allocated', 'width': '10%'},
                {'name': 'Used', 'width': '10%'},
                {'name': 'Carry Forward', 'width': '12%'},
                {'name': 'Balance', 'width': '10%'},
            ]
        }
        
        pdf_bytes = render_to_pdf("hr/export/leave_balances_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

class LeaveBalanceDetailExportView( StaffManagementRequiredMixin, View):
    """Export a single leave balance's details in CSV, Excel, or PDF."""

    def get(self, request, pk, *args, **kwargs):
        balance = get_object_or_404(LeaveBalance, pk=pk)
        format_type = request.GET.get('format', 'csv').lower()

        # Prepare data row with all fields
        row = {
            "employee_id": balance.staff.employee_id,
            "staff_name": balance.staff.user.get_full_name(),
            "staff_department": balance.staff.department.name if balance.staff.department else 'N/A',
            "staff_designation": balance.staff.designation.name if balance.staff.designation else 'N/A',
            "leave_type": balance.leave_type.name,
            "leave_code": balance.leave_type.code,
            "year": balance.year,
            "total_allocated": balance.total_allocated,
            "total_used": balance.total_used,
            "carry_forward": balance.carry_forward,
            "balance": balance.balance,
            "created_at": balance.created_at.strftime('%Y-%m-%d %H:%M'),
            "updated_at": balance.updated_at.strftime('%Y-%m-%d %H:%M'),
        }

        organization = get_user_institution(request.user)
        filename = f"leave_balance_{balance.staff.employee_id}_{balance.leave_type.code}_{balance.year}"

        if format_type == 'csv':
            return self.export_csv(row, filename, organization)
        elif format_type == 'excel':
            return self.export_excel(row, filename, organization)
        elif format_type == 'pdf':
            return self.export_pdf(row, filename, balance, organization)
        else:
            return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, row, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        # Header
        writer.writerow([
            'Employee ID', 'Staff Name', 'Department', 'Designation',
            'Leave Type', 'Leave Code', 'Year', 'Total Allocated', 'Total Used',
            'Carry Forward', 'Balance', 'Created At', 'Updated At'
        ])

        # Data
        writer.writerow([
            row['employee_id'], row['staff_name'], row['staff_department'], 
            row['staff_designation'], row['leave_type'], row['leave_code'],
            row['year'], row['total_allocated'], row['total_used'],
            row['carry_forward'], row['balance'], row['created_at'],
            row['updated_at']
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
            worksheet = workbook.add_worksheet('Leave Balance Detail')

            header_format = workbook.add_format({
                'bold': True, 
                'bg_color': '#3b5998', 
                'font_color': 'white', 
                'border': 1,
                'text_wrap': True
            })
            number_format = workbook.add_format({'num_format': '#,##0'})
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm'})
            center_format = workbook.add_format({'align': 'center'})

            headers = [
                'Employee ID', 'Staff Name', 'Department', 'Designation',
                'Leave Type', 'Leave Code', 'Year', 'Total Allocated', 'Total Used',
                'Carry Forward', 'Balance', 'Created At', 'Updated At'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            data = [
                row['employee_id'], row['staff_name'], row['staff_department'], 
                row['staff_designation'], row['leave_type'], row['leave_code'],
                row['year'], row['total_allocated'], row['total_used'],
                row['carry_forward'], row['balance'], row['created_at'],
                row['updated_at']
            ]
            
            for col, value in enumerate(data):
                fmt = None
                if col in [7, 8, 9, 10]:  # Numeric fields
                    fmt = number_format
                elif col in [6]:  # Year field
                    fmt = center_format
                elif col in [11, 12]:  # DateTime fields
                    fmt = date_format
                worksheet.write(1, col, value, fmt)

            worksheet.set_column('A:M', 18)

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

    def export_pdf(self, row, filename, balance, organization):
        context = {
            "balance": row,
            "original_balance": balance,
            "organization": organization,
            "export_date": timezone.now(),
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": f"Leave Balance - {row['employee_id']}",
        }
        
        pdf_bytes = render_to_pdf("hr/export/leave_balance_detail_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)