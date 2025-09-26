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
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View

from apps.core.mixins import StaffManagementRequiredMixin
from apps.core.utils import get_user_institution
from utils.utils import render_to_pdf, export_pdf_response

from .models import Payroll, Staff
from .forms import PayrollForm

class PayrollListView( StaffManagementRequiredMixin, ListView):
    model = Payroll
    template_name = 'hr/payroll/payroll_list.html'
    context_object_name = 'payrolls'
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
        
        # Filter by month
        month = self.request.GET.get('month')
        if month:
            queryset = queryset.filter(month=month)
        
        # Filter by year
        year = self.request.GET.get('year')
        if year:
            queryset = queryset.filter(year=year)
        
        # Filter by payment status
        payment_status = self.request.GET.get('payment_status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(staff__user__first_name__icontains=search_query) |
                Q(staff__user__last_name__icontains=search_query) |
                Q(staff__employee_id__icontains=search_query) |
                Q(payment_reference__icontains=search_query)
            )
        
        return queryset.select_related('staff', 'staff__user', 'institution').order_by('-year', '-month', 'staff__user__first_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add filter options
        institution = get_user_institution(user)
        if institution:
            context['staff_members'] = Staff.objects.filter(institution=institution, is_active=True)
        
        # Get unique years and months for filter dropdowns
        if institution:
            context['years'] = Payroll.objects.filter(
                institution=institution
            ).values_list('year', flat=True).distinct().order_by('-year')
            
            context['months'] = [
                (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
                (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
                (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
            ]
        
        # Payment status options
        context['payment_statuses'] = Payroll.PAYMENT_STATUS_CHOICES
        
        # Add statistics
        queryset = self.get_queryset()
        context['total_records'] = queryset.count()
        
        # Calculate totals
        total_earnings = queryset.aggregate(Sum('total_earnings'))['total_earnings__sum'] or 0
        total_deductions = queryset.aggregate(Sum('total_deductions'))['total_deductions__sum'] or 0
        total_net_salary = queryset.aggregate(Sum('net_salary'))['net_salary__sum'] or 0
        
        context['total_earnings'] = total_earnings
        context['total_deductions'] = total_deductions
        context['total_net_salary'] = total_net_salary
        
        # Payment status counts
        context['pending_count'] = queryset.filter(payment_status='pending').count()
        context['paid_count'] = queryset.filter(payment_status='paid').count()
        context['failed_count'] = queryset.filter(payment_status='failed').count()
        
        return context

class PayrollCreateView( StaffManagementRequiredMixin, CreateView):
    model = Payroll
    form_class = PayrollForm
    template_name = 'hr/payroll/payroll_form.html'
    success_url = reverse_lazy('hr:payroll_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        user = self.request.user
        institution = get_user_institution(user)
        
        if institution:
            form.instance.institution = institution
        
        messages.success(self.request, "Payroll record created successfully.")
        return super().form_valid(form)

class PayrollDetailView( StaffManagementRequiredMixin, DetailView):
    model = Payroll
    template_name = 'hr/payroll/payroll_detail.html'
    context_object_name = 'payroll'

class PayrollUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = Payroll
    form_class = PayrollForm
    template_name = 'hr/payroll/payroll_form.html'
    success_url = reverse_lazy('hr:payroll_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, "Payroll record updated successfully.")
        return super().form_valid(form)

class PayrollDeleteView( StaffManagementRequiredMixin, DeleteView):
    model = Payroll
    template_name = 'hr/payroll/payroll_confirm_delete.html'
    success_url = reverse_lazy('hr:payroll_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payroll = self.get_object()
        context['payroll'] = payroll
        context['organization'] = get_user_institution(self.request.user)
        context['title'] = "Delete Payroll Record"
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Payroll record deleted successfully.")
        return super().delete(request, *args, **kwargs)

class PayrollExportView( StaffManagementRequiredMixin, ListView):
    model = Payroll
    context_object_name = 'payrolls'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Payroll.objects.filter(institution=institution).select_related('staff', 'staff__user')
    
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        queryset = self.get_queryset()
        
        # Apply filters from request
        staff_id = request.GET.get('staff')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        
        month = request.GET.get('month')
        if month:
            queryset = queryset.filter(month=month)
        
        year = request.GET.get('year')
        if year:
            queryset = queryset.filter(year=year)
        
        payment_status = request.GET.get('payment_status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        # Build filename
        filename = f"payroll_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Build data rows
        rows = []
        for payroll in queryset:
            rows.append({
                "employee_id": payroll.staff.employee_id,
                "staff_name": payroll.staff.user.get_full_name(),
                "month": payroll.month,
                "year": payroll.year,
                "basic_salary": payroll.basic_salary,
                "house_rent_allowance": payroll.house_rent_allowance,
                "travel_allowance": payroll.travel_allowance,
                "medical_allowance": payroll.medical_allowance,
                "special_allowance": payroll.special_allowance,
                "performance_bonus": payroll.performance_bonus,
                "other_allowances": payroll.other_allowances,
                "professional_tax": payroll.professional_tax,
                "provident_fund": payroll.provident_fund,
                "income_tax": payroll.income_tax,
                "insurance": payroll.insurance,
                "loan_deductions": payroll.loan_deductions,
                "other_deductions": payroll.other_deductions,
                "total_earnings": payroll.total_earnings,
                "total_deductions": payroll.total_deductions,
                "net_salary": payroll.net_salary,
                "payment_date": payroll.payment_date.strftime('%Y-%m-%d') if payroll.payment_date else 'N/A',
                "payment_mode": payroll.get_payment_mode_display(),
                "payment_reference": payroll.payment_reference,
                "payment_status": payroll.get_payment_status_display(),
                "created_at": payroll.created_at.strftime('%Y-%m-%d %H:%M'),
                "updated_at": payroll.updated_at.strftime('%Y-%m-%d %H:%M'),
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
            'Employee ID', 'Staff Name', 'Month', 'Year', 'Basic Salary',
            'House Rent Allowance', 'Travel Allowance', 'Medical Allowance',
            'Special Allowance', 'Performance Bonus', 'Other Allowances',
            'Professional Tax', 'Provident Fund', 'Income Tax', 'Insurance',
            'Loan Deductions', 'Other Deductions', 'Total Earnings', 'Total Deductions',
            'Net Salary', 'Payment Date', 'Payment Mode', 'Payment Reference',
            'Payment Status', 'Created At', 'Updated At'
        ])
        
        # Write data rows
        for row in rows:
            writer.writerow([
                row['employee_id'],
                row['staff_name'],
                row['month'],
                row['year'],
                row['basic_salary'],
                row['house_rent_allowance'],
                row['travel_allowance'],
                row['medical_allowance'],
                row['special_allowance'],
                row['performance_bonus'],
                row['other_allowances'],
                row['professional_tax'],
                row['provident_fund'],
                row['income_tax'],
                row['insurance'],
                row['loan_deductions'],
                row['other_deductions'],
                row['total_earnings'],
                row['total_deductions'],
                row['net_salary'],
                row['payment_date'],
                row['payment_mode'],
                row['payment_reference'],
                row['payment_status'],
                row['created_at'],
                row['updated_at'],
            ])
        
        # Add summary row
        writer.writerow([])
        writer.writerow(['Total Records:', len(rows)])
        
        # Calculate totals
        total_earnings = sum(row['total_earnings'] for row in rows)
        total_deductions = sum(row['total_deductions'] for row in rows)
        total_net_salary = sum(row['net_salary'] for row in rows)
        
        writer.writerow(['Total Earnings:', total_earnings])
        writer.writerow(['Total Deductions:', total_deductions])
        writer.writerow(['Total Net Salary:', total_net_salary])
        
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    def export_excel(self, rows, filename, organization):
        """Export data to Excel format"""
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Payroll')
            
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
            datetime_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm'})
            center_format = workbook.add_format({'align': 'center'})
            
            # Write headers
            headers = [
                'Employee ID', 'Staff Name', 'Month', 'Year', 'Basic Salary',
                'House Rent Allowance', 'Travel Allowance', 'Medical Allowance',
                'Special Allowance', 'Performance Bonus', 'Other Allowances',
                'Professional Tax', 'Provident Fund', 'Income Tax', 'Insurance',
                'Loan Deductions', 'Other Deductions', 'Total Earnings', 'Total Deductions',
                'Net Salary', 'Payment Date', 'Payment Mode', 'Payment Reference',
                'Payment Status', 'Created At', 'Updated At'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Write data
            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data['employee_id'])
                worksheet.write(row_idx, 1, row_data['staff_name'])
                worksheet.write(row_idx, 2, row_data['month'], center_format)
                worksheet.write(row_idx, 3, row_data['year'], center_format)
                worksheet.write(row_idx, 4, float(row_data['basic_salary']), number_format)
                worksheet.write(row_idx, 5, float(row_data['house_rent_allowance']), number_format)
                worksheet.write(row_idx, 6, float(row_data['travel_allowance']), number_format)
                worksheet.write(row_idx, 7, float(row_data['medical_allowance']), number_format)
                worksheet.write(row_idx, 8, float(row_data['special_allowance']), number_format)
                worksheet.write(row_idx, 9, float(row_data['performance_bonus']), number_format)
                worksheet.write(row_idx, 10, float(row_data['other_allowances']), number_format)
                worksheet.write(row_idx, 11, float(row_data['professional_tax']), number_format)
                worksheet.write(row_idx, 12, float(row_data['provident_fund']), number_format)
                worksheet.write(row_idx, 13, float(row_data['income_tax']), number_format)
                worksheet.write(row_idx, 14, float(row_data['insurance']), number_format)
                worksheet.write(row_idx, 15, float(row_data['loan_deductions']), number_format)
                worksheet.write(row_idx, 16, float(row_data['other_deductions']), number_format)
                worksheet.write(row_idx, 17, float(row_data['total_earnings']), number_format)
                worksheet.write(row_idx, 18, float(row_data['total_deductions']), number_format)
                worksheet.write(row_idx, 19, float(row_data['net_salary']), number_format)
                worksheet.write(row_idx, 20, row_data['payment_date'] if row_data['payment_date'] != 'N/A' else '', date_format)
                worksheet.write(row_idx, 21, row_data['payment_mode'])
                worksheet.write(row_idx, 22, row_data['payment_reference'])
                worksheet.write(row_idx, 23, row_data['payment_status'])
                worksheet.write(row_idx, 24, row_data['created_at'], datetime_format)
                worksheet.write(row_idx, 25, row_data['updated_at'], datetime_format)
            
            # Adjust column widths
            worksheet.set_column('A:A', 15)  # Employee ID
            worksheet.set_column('B:B', 25)  # Staff Name
            worksheet.set_column('C:D', 10)  # Month, Year
            worksheet.set_column('E:T', 15)  # Numeric columns
            worksheet.set_column('U:U', 12)  # Payment Date
            worksheet.set_column('V:V', 15)  # Payment Mode
            worksheet.set_column('W:W', 20)  # Payment Reference
            worksheet.set_column('X:X', 15)  # Payment Status
            worksheet.set_column('Y:Z', 18)  # Date columns
            
            # Add summary
            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, 'Total Records:')
            worksheet.write(summary_row, 1, len(rows))
            
            # Calculate totals
            total_earnings = sum(float(row['total_earnings']) for row in rows)
            total_deductions = sum(float(row['total_deductions']) for row in rows)
            total_net_salary = sum(float(row['net_salary']) for row in rows)
            
            summary_row += 1
            worksheet.write(summary_row, 0, 'Total Earnings:')
            worksheet.write(summary_row, 1, total_earnings, number_format)
            
            summary_row += 1
            worksheet.write(summary_row, 0, 'Total Deductions:')
            worksheet.write(summary_row, 1, total_deductions, number_format)
            
            summary_row += 1
            worksheet.write(summary_row, 0, 'Total Net Salary:')
            worksheet.write(summary_row, 1, total_net_salary, number_format)
            
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
        total_earnings = sum(float(row['total_earnings']) for row in rows)
        total_deductions = sum(float(row['total_deductions']) for row in rows)
        total_net_salary = sum(float(row['net_salary']) for row in rows)
        
        context = {
            "payrolls": rows,
            "total_count": total_count,
            "total_earnings": total_earnings,
            "total_deductions": total_deductions,
            "total_net_salary": total_net_salary,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Payroll Export",
            "columns": [
                {'name': 'Employee ID', 'width': '10%'},
                {'name': 'Staff Name', 'width': '15%'},
                {'name': 'Period', 'width': '8%'},
                {'name': 'Basic Salary', 'width': '10%'},
                {'name': 'Total Earnings', 'width': '10%'},
                {'name': 'Total Deductions', 'width': '10%'},
                {'name': 'Net Salary', 'width': '10%'},
                {'name': 'Status', 'width': '8%'},
            ]
        }
        
        pdf_bytes = render_to_pdf("hr/export/payroll_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

class PayrollDetailExportView( StaffManagementRequiredMixin, View):
    """Export a single payroll record's details in CSV, Excel, or PDF."""

    def get(self, request, pk, *args, **kwargs):
        payroll = get_object_or_404(Payroll, pk=pk)
        format_type = request.GET.get('format', 'csv').lower()

        # Prepare data row with all fields
        row = {
            "employee_id": payroll.staff.employee_id,
            "staff_name": payroll.staff.user.get_full_name(),
            "staff_department": payroll.staff.department.name if payroll.staff.department else 'N/A',
            "staff_designation": payroll.staff.designation.name if payroll.staff.designation else 'N/A',
            "month": payroll.month,
            "year": payroll.year,
            "basic_salary": payroll.basic_salary,
            "house_rent_allowance": payroll.house_rent_allowance,
            "travel_allowance": payroll.travel_allowance,
            "medical_allowance": payroll.medical_allowance,
            "special_allowance": payroll.special_allowance,
            "performance_bonus": payroll.performance_bonus,
            "other_allowances": payroll.other_allowances,
            "professional_tax": payroll.professional_tax,
            "provident_fund": payroll.provident_fund,
            "income_tax": payroll.income_tax,
            "insurance": payroll.insurance,
            "loan_deductions": payroll.loan_deductions,
            "other_deductions": payroll.other_deductions,
            "total_earnings": payroll.total_earnings,
            "total_deductions": payroll.total_deductions,
            "net_salary": payroll.net_salary,
            "payment_date": payroll.payment_date.strftime('%Y-%m-%d') if payroll.payment_date else 'N/A',
            "payment_mode": payroll.get_payment_mode_display(),
            "payment_reference": payroll.payment_reference,
            "payment_status": payroll.get_payment_status_display(),
            "created_at": payroll.created_at.strftime('%Y-%m-%d %H:%M'),
            "updated_at": payroll.updated_at.strftime('%Y-%m-%d %H:%M'),
        }

        organization = get_user_institution(request.user)
        filename = f"payroll_{payroll.staff.employee_id}_{payroll.month}_{payroll.year}"

        if format_type == 'csv':
            return self.export_csv(row, filename, organization)
        elif format_type == 'excel':
            return self.export_excel(row, filename, organization)
        elif format_type == 'pdf':
            return self.export_pdf(row, filename, payroll, organization)
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
            ('Period', f"{row['month']}/{row['year']}"),
            ('Basic Salary', row['basic_salary']),
            ('House Rent Allowance', row['house_rent_allowance']),
            ('Travel Allowance', row['travel_allowance']),
            ('Medical Allowance', row['medical_allowance']),
            ('Special Allowance', row['special_allowance']),
            ('Performance Bonus', row['performance_bonus']),
            ('Other Allowances', row['other_allowances']),
            ('Professional Tax', row['professional_tax']),
            ('Provident Fund', row['provident_fund']),
            ('Income Tax', row['income_tax']),
            ('Insurance', row['insurance']),
            ('Loan Deductions', row['loan_deductions']),
            ('Other Deductions', row['other_deductions']),
            ('Total Earnings', row['total_earnings']),
            ('Total Deductions', row['total_deductions']),
            ('Net Salary', row['net_salary']),
            ('Payment Date', row['payment_date']),
            ('Payment Mode', row['payment_mode']),
            ('Payment Reference', row['payment_reference']),
            ('Payment Status', row['payment_status']),
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
            worksheet = workbook.add_worksheet('Payroll Detail')

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
                ('Period', f"{row['month']}/{row['year']}"),
                ('', ''),  # Empty row for spacing
                ('EARNINGS', ''),
                ('Basic Salary', row['basic_salary']),
                ('House Rent Allowance', row['house_rent_allowance']),
                ('Travel Allowance', row['travel_allowance']),
                ('Medical Allowance', row['medical_allowance']),
                ('Special Allowance', row['special_allowance']),
                ('Performance Bonus', row['performance_bonus']),
                ('Other Allowances', row['other_allowances']),
                ('Total Earnings', row['total_earnings']),
                ('', ''),  # Empty row for spacing
                ('DEDUCTIONS', ''),
                ('Professional Tax', row['professional_tax']),
                ('Provident Fund', row['provident_fund']),
                ('Income Tax', row['income_tax']),
                ('Insurance', row['insurance']),
                ('Loan Deductions', row['loan_deductions']),
                ('Other Deductions', row['other_deductions']),
                ('Total Deductions', row['total_deductions']),
                ('', ''),  # Empty row for spacing
                ('NET SALARY', row['net_salary']),
                ('', ''),  # Empty row for spacing
                ('PAYMENT DETAILS', ''),
                ('Payment Date', row['payment_date']),
                ('Payment Mode', row['payment_mode']),
                ('Payment Reference', row['payment_reference']),
                ('Payment Status', row['payment_status']),
                ('', ''),  # Empty row for spacing
                ('Created At', row['created_at']),
                ('Updated At', row['updated_at']),
            ]

            for row_idx, (field, value) in enumerate(fields, start=1):
                worksheet.write(row_idx, 0, field, bold_format if field in ['EARNINGS', 'DEDUCTIONS', 'NET SALARY', 'PAYMENT DETAILS'] else None)
                
                if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '').isdigit()):
                    worksheet.write(row_idx, 1, float(value), number_format)
                else:
                    worksheet.write(row_idx, 1, value)

            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:B', 20)

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

    def export_pdf(self, row, filename, payroll, organization):
        context = {
            "payroll": row,
            "original_payroll": payroll,
            "organization": organization,
            "export_date": timezone.now(),
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": f"Payroll - {row['employee_id']}",
        }
        
        pdf_bytes = render_to_pdf("hr/export/payroll_detail_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)