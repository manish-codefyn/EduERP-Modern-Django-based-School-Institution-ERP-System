import csv
import io

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView,View
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Q
from .models import Staff,Designation,Department
from apps.organization.models import Institution
from apps.core.mixins import HRManagementRequiredMixin,StaffManagementRequiredMixin, DirectorRequiredMixin
from apps.core.utils import get_user_institution

from datetime import datetime
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import StaffManagementRequiredMixin
from apps.core.utils import get_user_institution
from utils.utils import render_to_pdf, export_pdf_response,qr_generate
import xlsxwriter
from io import BytesIO, StringIO
from .forms import StaffForm,StaffFilterForm


from .idcard import StaffIDCardGenerator


def generate_staff_id_card(request, staff_id):
    staff = Staff.objects.get(id=staff_id)
    
    # Get logo and stamp paths from your organization model
    institution = staff.institution
    logo_path = institution.logo.path if institution.logo else None
    stamp_path = institution.stamp.path if institution.stamp else None
    
    generator = StaffIDCardGenerator(staff, logo_path, stamp_path)
    return generator.get_id_card_response()


class StaffCreateView( StaffManagementRequiredMixin, CreateView):
    model = Staff
    form_class = StaffForm
    template_name = 'hr/staff/staff_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['institution'] = get_user_institution(self.request.user)
        return kwargs
    
    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, 'Staff member created successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('hr:staff_list')


class StaffUpdateView( StaffManagementRequiredMixin, UpdateView):
    model = Staff
    form_class = StaffForm
    template_name = 'hr/staff/staff_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['institution'] = get_user_institution(self.request.user)
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Staff member updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('hr:staff_list')


class StaffListView( StaffManagementRequiredMixin, ListView):
    model = Staff
    template_name = 'hr/staff/staff_list.html'
    context_object_name = 'staff_list'
    paginate_by = 20
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = Staff.objects.filter(institution=institution).select_related(
            'user', 'department', 'designation'
        )
        
        # Apply filters
        form = StaffFilterForm(self.request.GET, institution=institution)
        if form.is_valid():
            status = form.cleaned_data.get('status')
            staff_type = form.cleaned_data.get('staff_type')
            department = form.cleaned_data.get('department')
            designation = form.cleaned_data.get('designation')
            employment_type = form.cleaned_data.get('employment_type')
            search = form.cleaned_data.get('search')
            
            if status == 'active':
                queryset = queryset.filter(is_active=True)
            elif status == 'inactive':
                queryset = queryset.filter(is_active=False)
                
            if staff_type:
                queryset = queryset.filter(staff_type=staff_type)
                
            if department:
                queryset = queryset.filter(department=department)
                
            if designation:
                queryset = queryset.filter(designation=designation)
                
            if employment_type:
                queryset = queryset.filter(employment_type=employment_type)
                
            if search:
                queryset = queryset.filter(
                    Q(user__first_name__icontains=search) |
                    Q(user__last_name__icontains=search) |
                    Q(employee_id__icontains=search)
                )
        
        return queryset.order_by('user__last_name', 'user__first_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Add filter form to context
        context['filter_form'] = StaffFilterForm(self.request.GET, institution=institution)
        
        # Add choices for template (if needed for manual rendering)
        context['staff_types'] = [('', 'All Types')] + list(Staff.STAFF_TYPE_CHOICES)
        context['departments'] = Department.objects.filter(institution=institution)
        context['designations'] = Designation.objects.filter(institution=institution)
        
        
         # --- Stats for cards ---
        all_staff = Staff.objects.filter(institution=institution)
        context['total_staff'] = all_staff.count()
        context['active_staff'] = all_staff.filter(is_active=True).count()
        context['teaching_staff'] = all_staff.filter(staff_type='teaching').count()
        context['non_teaching_staff'] = all_staff.filter(staff_type='non-teaching').count()
        
        return context


class StaffDetailView(  StaffManagementRequiredMixin, DetailView):
    model = Staff
    template_name = 'hr/staff/staff_detail.html'
    context_object_name = 'staff'


class StaffDeleteView( DirectorRequiredMixin, DeleteView):
    model = Staff
    template_name = 'hr/staff/staff_confirm_delete.html'
    
    def get_success_url(self):
        messages.success(self.request, 'Staff member deleted successfully!')
        return reverse_lazy('hr:staff_list')



class StaffExportView( StaffManagementRequiredMixin, ListView):
    model = Staff
    context_object_name = 'staff_list'
    
    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Staff.objects.filter(institution=institution)
    
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        queryset = self.get_queryset()
        
        # Build filename
        filename = f"staff_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Build data rows
        rows = []
        for staff in queryset:
            rows.append({
                "employee_id": staff.employee_id,
                "name": staff.user.get_full_name(),
                "staff_type": staff.get_staff_type_display(),
                "department": staff.department.name if staff.department else '',
                "designation": staff.designation.name if staff.designation else '',
                "employment_type": staff.get_employment_type_display(),
                "joining_date": staff.joining_date.strftime('%Y-%m-%d') if staff.joining_date else '',
                "salary": float(staff.salary) if staff.salary else 0.0,
                "status": "Active" if staff.is_active else "Inactive"
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
            'Employee ID', 'Name', 'Staff Type', 'Department', 'Designation',
            'Employment Type', 'Joining Date', 'Salary', 'Status'
        ])
        
        # Write data rows
        for row in rows:
            writer.writerow([
                row['employee_id'],
                row['name'],
                row['staff_type'],
                row['department'],
                row['designation'],
                row['employment_type'],
                row['joining_date'],
                row['salary'],
                row['status']
            ])
        
        # Add summary row
        writer.writerow([])
        writer.writerow(['Total Staff:', len(rows)])
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    def export_excel(self, rows, filename, organization):
        """Export data to Excel format"""
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Staff List')
            
            # Add formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#3b5998',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            money_format = workbook.add_format({'num_format': '₹#,##0.00'})
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            center_format = workbook.add_format({'align': 'center'})
            
            # Write headers
            headers = [
                'Employee ID', 'Name', 'Staff Type', 'Department', 'Designation',
                'Employment Type', 'Joining Date', 'Salary', 'Status'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Write data
            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data['employee_id'])
                worksheet.write(row_idx, 1, row_data['name'])
                worksheet.write(row_idx, 2, row_data['staff_type'])
                worksheet.write(row_idx, 3, row_data['department'])
                worksheet.write(row_idx, 4, row_data['designation'])
                worksheet.write(row_idx, 5, row_data['employment_type'])
                worksheet.write(row_idx, 6, row_data['joining_date'], date_format)
                worksheet.write(row_idx, 7, row_data['salary'], money_format)
                worksheet.write(row_idx, 8, row_data['status'], center_format)
            
            # Adjust column widths
            worksheet.set_column('A:A', 15)  # Employee ID
            worksheet.set_column('B:B', 25)  # Name
            worksheet.set_column('C:C', 20)  # Staff Type
            worksheet.set_column('D:D', 20)  # Department
            worksheet.set_column('E:E', 20)  # Designation
            worksheet.set_column('F:F', 15)  # Employment Type
            worksheet.set_column('G:G', 15)  # Joining Date
            worksheet.set_column('H:H', 15)  # Salary
            worksheet.set_column('I:I', 10)  # Status
            
            # Add summary
            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, 'Total Staff:')
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
    
    def export_pdf(self, rows, filename, organization, total_count):
        """Export data to PDF format"""
        context = {
            "staff_list": rows,
            "total_count": total_count,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Staff List Export",
            "columns": [
                {'name': 'Employee ID', 'width': '15%'},
                {'name': 'Name', 'width': '25%'},
                {'name': 'Staff Type', 'width': '15%'},
                {'name': 'Department', 'width': '15%'},
                {'name': 'Designation', 'width': '15%'},
                {'name': 'Status', 'width': '10%'},
            ]
        }
        
        pdf_bytes = render_to_pdf("hr/export/staff_list_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)
    

class StaffDetailExportView( StaffManagementRequiredMixin, View):
    """Export a single staff member's details in CSV, Excel, or PDF, with QR code."""

    def get(self, request, pk, *args, **kwargs):
        staff = get_object_or_404(Staff, pk=pk)
        format_type = request.GET.get('format', 'csv').lower()

        # Prepare data row with all fields
        row = {
            "employee_id": staff.employee_id,
            "name": staff.user.get_full_name(),
            "staff_type": staff.get_staff_type_display(),
            "department": staff.department.name if staff.department else 'N/A',
            "designation": staff.designation.name if staff.designation else 'N/A',
            "employment_type": staff.get_employment_type_display(),
            "joining_date": staff.joining_date.strftime('%Y-%m-%d') if staff.joining_date else 'N/A',
            "salary": float(staff.salary) if staff.salary else 0.0,
            "status": "Active" if staff.is_active else "Inactive",
            
            # Personal Information
            "date_of_birth": staff.date_of_birth.strftime('%Y-%m-%d') if staff.date_of_birth else 'N/A',
            "gender": staff.get_gender_display() if staff.gender else 'N/A',
            "blood_group": staff.get_blood_group_display() if staff.blood_group else 'N/A',
            "marital_status": staff.marital_status.title() if staff.marital_status else 'N/A',
            
            # Contact Information
            "personal_email": staff.personal_email or 'N/A',
            "personal_phone": staff.personal_phone or 'N/A',
            "emergency_contact_name": staff.emergency_contact_name or 'N/A',
            "emergency_contact_phone": staff.emergency_contact_phone or 'N/A',
            "emergency_contact_relation": staff.emergency_contact_relation or 'N/A',
            
            # Employment Details
            "contract_end_date": staff.contract_end_date.strftime('%Y-%m-%d') if staff.contract_end_date else 'N/A',
            "probation_end_date": staff.probation_end_date.strftime('%Y-%m-%d') if staff.probation_end_date else 'N/A',
            "resignation_date": staff.resignation_date.strftime('%Y-%m-%d') if staff.resignation_date else 'N/A',
            "resignation_reason": staff.resignation_reason or 'N/A',
            
            # Financial Information
            "bank_account": staff.bank_account or 'N/A',
            "bank_name": staff.bank_name or 'N/A',
            "ifsc_code": staff.ifsc_code or 'N/A',
            "pan_number": staff.pan_number or 'N/A',
            "aadhaar_number": staff.aadhaar_number or 'N/A',
        }

        organization = get_user_institution(request.user)
        filename = f"staff_{staff.employee_id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        # Generate QR code for staff
        qr_code_img = qr_generate(f"{staff.employee_id} - {staff.user.get_full_name()}")

        if format_type == 'csv':
            return self.export_csv(row, filename, organization)
        elif format_type == 'excel':
            return self.export_excel(row, filename, organization)
        elif format_type == 'pdf':
            return self.export_pdf(row, filename, staff, organization, qr_code_img)
        else:
            return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, row, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        # Header
        writer.writerow([
            'Employee ID', 'Name', 'Staff Type', 'Department', 'Designation',
            'Employment Type', 'Joining Date', 'Salary', 'Status', 'Date of Birth',
            'Gender', 'Blood Group', 'Marital Status', 'Personal Email', 'Personal Phone',
            'Emergency Contact', 'Emergency Phone', 'Emergency Relation', 'Bank Name',
            'Account Number', 'IFSC Code', 'PAN Number', 'Aadhaar Number'
        ])

        # Data
        writer.writerow([
            row['employee_id'], row['name'], row['staff_type'], row['department'],
            row['designation'], row['employment_type'], row['joining_date'],
            row['salary'], row['status'], row['date_of_birth'], row['gender'],
            row['blood_group'], row['marital_status'], row['personal_email'],
            row['personal_phone'], row['emergency_contact_name'], 
            row['emergency_contact_phone'], row['emergency_contact_relation'],
            row['bank_name'], row['bank_account'], row['ifsc_code'], 
            row['pan_number'], row['aadhaar_number']
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
            worksheet = workbook.add_worksheet('Staff Detail')

            header_format = workbook.add_format({'bold': True, 'bg_color': '#3b5998', 'font_color': 'white', 'border':1})
            money_format = workbook.add_format({'num_format': '₹#,##0.00'})
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})

            headers = [
                'Employee ID', 'Name', 'Staff Type', 'Department', 'Designation',
                'Employment Type', 'Joining Date', 'Salary', 'Status', 'Date of Birth',
                'Gender', 'Blood Group', 'Marital Status', 'Personal Email', 'Personal Phone',
                'Emergency Contact', 'Emergency Phone', 'Emergency Relation', 'Bank Name',
                'Account Number', 'IFSC Code', 'PAN Number', 'Aadhaar Number'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            data = [
                row['employee_id'], row['name'], row['staff_type'], row['department'],
                row['designation'], row['employment_type'], row['joining_date'],
                row['salary'], row['status'], row['date_of_birth'], row['gender'],
                row['blood_group'], row['marital_status'], row['personal_email'],
                row['personal_phone'], row['emergency_contact_name'], 
                row['emergency_contact_phone'], row['emergency_contact_relation'],
                row['bank_name'], row['bank_account'], row['ifsc_code'], 
                row['pan_number'], row['aadhaar_number']
            ]
            
            for col, value in enumerate(data):
                fmt = money_format if col == 7 else date_format if col in [6, 9] else None
                worksheet.write(1, col, value, fmt)

            worksheet.set_column('A:W', 20)

            # Summary
            worksheet.write(3, 0, 'Organization:')
            worksheet.write(3, 1, organization.name if organization else 'N/A')
            worksheet.write(4, 0, 'Export Date:')
            worksheet.write(4, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))

        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(),
                                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, row, filename, staff, organization, qr_code_img):
        context = {
            "staff": row,
            "photo": getattr(staff.photo, 'url', None) if staff.photo and staff else None,
            "full_name": staff.user.get_full_name(),  # Fixed: Added parentheses
            "organization": organization,
            "export_date": timezone.now(),
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": f"Staff Detail - {row['employee_id']}",
            "qr_code": qr_code_img,  # Pass QR code image to template
        }
        pdf_bytes = render_to_pdf("hr/export/staff_detail_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)