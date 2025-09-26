
import csv
import xlsxwriter
from io import StringIO, BytesIO
from datetime import datetime
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView,View
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from apps.core.mixins import StaffManagementRequiredMixin,DirectorRequiredMixin
from apps.core.utils import get_user_institution
from utils.utils import  render_to_pdf, export_pdf_response, qr_generate
from .models import Faculty
from .forms import FacultyForm
from .faculty_icard import FacultyIDCardGenerator


def generate_faculty_id_card(request, faculty_id):
    faculty = get_object_or_404(Faculty, id=faculty_id)
    # Faculty is always linked to Staff

    # Get logo and stamp paths from the institution via Staff
    institution = faculty.staff.institution
    logo_path = institution.logo.path if institution and institution.logo else None
    stamp_path = institution.stamp.path if institution and institution.stamp else None

    # Reuse your staff ID card generator
    generator = FacultyIDCardGenerator(faculty, logo_path, stamp_path)
    return generator.get_id_card_response()


class FacultyListView(DirectorRequiredMixin, ListView):
    model = Faculty
    template_name = 'hr/faculty/faculty_list.html'
    context_object_name = 'faculties'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        institute = get_user_institution(self.request.user)
        
        # Filter by institute if applicable
        if institute:
            queryset = queryset.filter(staff__institution=institute)
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(staff__user__first_name__icontains=search_query) |
                Q(staff__user__last_name__icontains=search_query) |
                Q(qualification__icontains=search_query) |
                Q(specialization__icontains=search_query) |
                Q(degree__icontains=search_query) |
                Q(university__icontains=search_query)
            )
        
        # Filter by qualification
        qualification = self.request.GET.get('qualification')
        if qualification:
            queryset = queryset.filter(qualification=qualification)
        
        # Filter by specialization
        specialization = self.request.GET.get('specialization')
        if specialization:
            queryset = queryset.filter(specialization=specialization)
            
        # Filter by class teacher status
        is_class_teacher = self.request.GET.get('is_class_teacher')
        if is_class_teacher == 'true':
            queryset = queryset.filter(is_class_teacher=True)
        elif is_class_teacher == 'false':
            queryset = queryset.filter(is_class_teacher=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        
        context['qualification_choices'] = Faculty.QUALIFICATION_CHOICES
        context['specialization_choices'] = Faculty.SPECIALIZATION_CHOICES
        
        # Add statistics for the dashboard cards
        context['total_faculty'] = queryset.count()
        context['class_teachers_count'] = queryset.filter(is_class_teacher=True).count()
        context['phd_count'] = queryset.filter(qualification='phd').count()
        
        # Calculate average experience
        total_experience = queryset.aggregate(Sum('total_experience'))['total_experience__sum']
        context['avg_experience'] = round(total_experience / context['total_faculty'], 1) if context['total_faculty'] > 0 else 0
        
        return context

class FacultyCreateView(DirectorRequiredMixin, CreateView):
    model = Faculty
    form_class = FacultyForm
    template_name = 'hr/faculty/faculty_form.html'
    success_url = reverse_lazy('hr:faculty_list')
    
    def form_valid(self, form):
        # Set the institute for the staff member if needed
        response = super().form_valid(form)
        messages.success(self.request, 'Faculty member created successfully.')
        return response


class FacultyUpdateView(DirectorRequiredMixin, UpdateView):
    model = Faculty
    form_class = FacultyForm
    template_name = 'hr/faculty/faculty_form.html'
    success_url = reverse_lazy('hr:faculty_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Faculty member updated successfully.')
        return response


class FacultyDeleteView(DirectorRequiredMixin, DeleteView):
    model = Faculty
    template_name = 'hr/faculty/faculty_confirm_delete.html'
    success_url = reverse_lazy('hr:faculty_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Faculty member deleted successfully.')
        return super().delete(request, *args, **kwargs)


class FacultyDetailView(DirectorRequiredMixin, DetailView):
    model = Faculty
    template_name = 'hr/faculty/faculty_detail.html'
    context_object_name = 'faculty'


class FacultyExportView( DirectorRequiredMixin, ListView):
    model = Faculty
    context_object_name = 'faculties'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        institute = get_user_institution(self.request.user)
        
        if institute:
            queryset = queryset.filter(staff__institution=institute)
        
        return queryset
    
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        queryset = self.get_queryset()
        
        # Build filename
        filename = f"faculty_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Build data rows
        rows = []
        for faculty in queryset:
            rows.append({
                "name": f"Prof. {faculty.staff.user.get_full_name()}",
                "qualification": faculty.get_qualification_display(),
                "degree": faculty.degree,
                "specialization": faculty.get_specialization_display(),
                "year_of_graduation": faculty.year_of_graduation,
                "university": faculty.university,
                "total_experience": faculty.total_experience,
                "research_publications": faculty.research_publications,
                "is_class_teacher": "Yes" if faculty.is_class_teacher else "No",
                "class_teacher_of": str(faculty.class_teacher_of) if faculty.class_teacher_of else 'N/A',
                "office_hours": faculty.office_hours or 'N/A',
                "office_location": faculty.office_location or 'N/A',
                "created_at": faculty.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "subjects": ", ".join([subject.name for subject in faculty.subjects.all()]),
                "training_courses": faculty.training_courses or 'N/A',
                "conferences_attended": faculty.conferences_attended or 'N/A',
                "awards": faculty.awards or 'N/A',
                "designation": faculty.current_designation,
                "email": faculty.staff.user.email,
                "phone": faculty.staff.personal_phone or 'N/A'
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
            'Name', 'Designation', 'Email', 'Phone', 'Qualification', 'Degree', 
            'Specialization', 'Year of Graduation', 'University', 'Total Experience (Years)',
            'Research Publications', 'Is Class Teacher', 'Class Teacher Of', 'Subjects',
            'Office Hours', 'Office Location', 'Training Courses', 'Conferences Attended',
            'Awards', 'Created At'
        ])
        
        # Write data rows
        for row in rows:
            writer.writerow([
                row['name'],
                row['designation'],
                row['email'],
                row['phone'],
                row['qualification'],
                row['degree'],
                row['specialization'],
                row['year_of_graduation'],
                row['university'],
                row['total_experience'],
                row['research_publications'],
                row['is_class_teacher'],
                row['class_teacher_of'],
                row['subjects'],
                row['office_hours'],
                row['office_location'],
                row['training_courses'],
                row['conferences_attended'],
                row['awards'],
                row['created_at']
            ])
        
        # Add summary row
        writer.writerow([])
        writer.writerow(['Total Faculty:', len(rows)])
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    def export_excel(self, rows, filename, organization):
        """Export data to Excel format"""
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Faculty List')
            
            # Add formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#3b5998',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
            center_format = workbook.add_format({'align': 'center'})
            
            # Write headers
            headers = [
                'Name', 'Designation', 'Email', 'Phone', 'Qualification', 'Degree', 
                'Specialization', 'Year of Graduation', 'University', 'Total Experience (Years)',
                'Research Publications', 'Is Class Teacher', 'Class Teacher Of', 'Subjects',
                'Office Hours', 'Office Location', 'Training Courses', 'Conferences Attended',
                'Awards', 'Created At'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Write data
            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data['name'])
                worksheet.write(row_idx, 1, row_data['designation'])
                worksheet.write(row_idx, 2, row_data['email'])
                worksheet.write(row_idx, 3, row_data['phone'])
                worksheet.write(row_idx, 4, row_data['qualification'])
                worksheet.write(row_idx, 5, row_data['degree'])
                worksheet.write(row_idx, 6, row_data['specialization'])
                worksheet.write(row_idx, 7, row_data['year_of_graduation'])
                worksheet.write(row_idx, 8, row_data['university'])
                worksheet.write(row_idx, 9, row_data['total_experience'])
                worksheet.write(row_idx, 10, row_data['research_publications'])
                worksheet.write(row_idx, 11, row_data['is_class_teacher'], center_format)
                worksheet.write(row_idx, 12, row_data['class_teacher_of'])
                worksheet.write(row_idx, 13, row_data['subjects'])
                worksheet.write(row_idx, 14, row_data['office_hours'])
                worksheet.write(row_idx, 15, row_data['office_location'])
                worksheet.write(row_idx, 16, row_data['training_courses'])
                worksheet.write(row_idx, 17, row_data['conferences_attended'])
                worksheet.write(row_idx, 18, row_data['awards'])
                worksheet.write(row_idx, 19, row_data['created_at'], date_format)
            
            # Adjust column widths
            worksheet.set_column('A:A', 25)  # Name
            worksheet.set_column('B:B', 20)  # Designation
            worksheet.set_column('C:C', 25)  # Email
            worksheet.set_column('D:D', 15)  # Phone
            worksheet.set_column('E:E', 15)  # Qualification
            worksheet.set_column('F:F', 20)  # Degree
            worksheet.set_column('G:G', 20)  # Specialization
            worksheet.set_column('H:H', 15)  # Year of Graduation
            worksheet.set_column('I:I', 25)  # University
            worksheet.set_column('J:J', 20)  # Total Experience
            worksheet.set_column('K:K', 20)  # Research Publications
            worksheet.set_column('L:L', 15)  # Is Class Teacher
            worksheet.set_column('M:M', 20)  # Class Teacher Of
            worksheet.set_column('N:N', 30)  # Subjects
            worksheet.set_column('O:O', 20)  # Office Hours
            worksheet.set_column('P:P', 20)  # Office Location
            worksheet.set_column('Q:Q', 30)  # Training Courses
            worksheet.set_column('R:R', 30)  # Conferences Attended
            worksheet.set_column('S:S', 30)  # Awards
            worksheet.set_column('T:T', 20)  # Created At
            
            # Add summary
            summary_row = len(rows) + 2
            worksheet.write(summary_row, 0, 'Total Faculty:')
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
            "faculty_list": rows,
            "total_count": total_count,
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Faculty List Export",
            "columns": [
                {'name': 'Name', 'width': '20%'},
                {'name': 'Designation', 'width': '15%'},
                {'name': 'Qualification', 'width': '15%'},
                {'name': 'Specialization', 'width': '15%'},
                {'name': 'Experience', 'width': '10%'},
                {'name': 'Class Teacher', 'width': '10%'},
                {'name': 'Publications', 'width': '10%'},
            ]
        }
        
        pdf_bytes = render_to_pdf("hr/export/faculty_list_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)


class FacultyDetailExportView( DirectorRequiredMixin, View):
    """Export a single faculty member's details in CSV, Excel, or PDF, with QR code."""

    def get(self, request, pk, *args, **kwargs):
        faculty = get_object_or_404(Faculty, pk=pk)
        format_type = request.GET.get('format', 'csv').lower()

        # Prepare data row with all fields
        row = {
            "name": f"Prof. {faculty.staff.user.get_full_name()}",
            "designation": faculty.current_designation,
            "email": faculty.staff.user.email,
            "phone": faculty.staff.personal_phone or 'N/A',
            "qualification": faculty.get_qualification_display(),
            "degree": faculty.degree,
            "specialization": faculty.get_specialization_display(),
            "year_of_graduation": faculty.year_of_graduation,
            "university": faculty.university,
            "total_experience": faculty.total_experience,
            "research_publications": faculty.research_publications,
            "is_class_teacher": "Yes" if faculty.is_class_teacher else "No",
            "class_teacher_of": str(faculty.class_teacher_of) if faculty.class_teacher_of else 'N/A',
            "office_hours": faculty.office_hours or 'N/A',
            "office_location": faculty.office_location or 'N/A',
            "created_at": faculty.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "subjects": ", ".join([subject.name for subject in faculty.subjects.all()]),
            "training_courses": faculty.training_courses or 'N/A',
            "conferences_attended": faculty.conferences_attended or 'N/A',
            "awards": faculty.awards or 'N/A',
            
            # Personal Information from Staff
            "date_of_birth": faculty.staff.date_of_birth.strftime('%Y-%m-%d') if faculty.staff.date_of_birth else 'N/A',
            "gender": faculty.staff.get_gender_display() if faculty.staff.gender else 'N/A',
            "blood_group": faculty.staff.get_blood_group_display() if faculty.staff.blood_group else 'N/A',
            "marital_status": faculty.staff.marital_status.title() if faculty.staff.marital_status else 'N/A',
            
            # Contact Information
            "personal_email": faculty.staff.personal_email or 'N/A',
            "personal_phone": faculty.staff.personal_phone or 'N/A',
            "emergency_contact_name": faculty.staff.emergency_contact_name or 'N/A',
            "emergency_contact_phone": faculty.staff.emergency_contact_phone or 'N/A',
            "emergency_contact_relation": faculty.staff.emergency_contact_relation or 'N/A',
            
            # Employment Details
            "joining_date": faculty.staff.joining_date.strftime('%Y-%m-%d') if faculty.staff.joining_date else 'N/A',
            "contract_end_date": faculty.staff.contract_end_date.strftime('%Y-%m-%d') if faculty.staff.contract_end_date else 'N/A',
            
            # Financial Information
            "bank_account": faculty.staff.bank_account or 'N/A',
            "bank_name": faculty.staff.bank_name or 'N/A',
            "ifsc_code": faculty.staff.ifsc_code or 'N/A',
            "pan_number": faculty.staff.pan_number or 'N/A',
            "aadhaar_number": faculty.staff.aadhaar_number or 'N/A',
        }

        organization = get_user_institution(request.user)
        filename = f"faculty_{faculty.staff.employee_id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        # Generate QR code for faculty
        qr_code_img = qr_generate(f"{faculty.staff.employee_id} - {faculty.staff.user.get_full_name()}")

        if format_type == 'csv':
            return self.export_csv(row, filename, organization)
        elif format_type == 'excel':
            return self.export_excel(row, filename, organization)
        elif format_type == 'pdf':
            return self.export_pdf(row, filename, faculty, organization, qr_code_img)
        else:
            return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, row, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)

        # Header
        writer.writerow([
            'Name', 'Designation', 'Email', 'Phone', 'Qualification', 'Degree', 
            'Specialization', 'Year of Graduation', 'University', 'Total Experience',
            'Research Publications', 'Is Class Teacher', 'Class Teacher Of', 'Subjects',
            'Office Hours', 'Office Location', 'Training Courses', 'Conferences Attended',
            'Awards', 'Date of Birth', 'Gender', 'Blood Group', 'Marital Status',
            'Personal Email', 'Personal Phone', 'Emergency Contact', 'Emergency Phone',
            'Emergency Relation', 'Joining Date', 'Bank Name', 'Account Number', 
            'IFSC Code', 'PAN Number', 'Aadhaar Number'
        ])

        # Data
        writer.writerow([
            row['name'], row['designation'], row['email'], row['phone'],
            row['qualification'], row['degree'], row['specialization'],
            row['year_of_graduation'], row['university'], row['total_experience'],
            row['research_publications'], row['is_class_teacher'], row['class_teacher_of'],
            row['subjects'], row['office_hours'], row['office_location'],
            row['training_courses'], row['conferences_attended'], row['awards'],
            row['date_of_birth'], row['gender'], row['blood_group'], row['marital_status'],
            row['personal_email'], row['personal_phone'], row['emergency_contact_name'],
            row['emergency_contact_phone'], row['emergency_contact_relation'],
            row['joining_date'], row['bank_name'], row['bank_account'], row['ifsc_code'],
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
            worksheet = workbook.add_worksheet('Faculty Detail')

            header_format = workbook.add_format({'bold': True, 'bg_color': '#3b5998', 'font_color': 'white', 'border':1})
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})

            headers = [
                'Name', 'Designation', 'Email', 'Phone', 'Qualification', 'Degree', 
                'Specialization', 'Year of Graduation', 'University', 'Total Experience',
                'Research Publications', 'Is Class Teacher', 'Class Teacher Of', 'Subjects',
                'Office Hours', 'Office Location', 'Training Courses', 'Conferences Attended',
                'Awards', 'Date of Birth', 'Gender', 'Blood Group', 'Marital Status',
                'Personal Email', 'Personal Phone', 'Emergency Contact', 'Emergency Phone',
                'Emergency Relation', 'Joining Date', 'Bank Name', 'Account Number', 
                'IFSC Code', 'PAN Number', 'Aadhaar Number'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            data = [
                row['name'], row['designation'], row['email'], row['phone'],
                row['qualification'], row['degree'], row['specialization'],
                row['year_of_graduation'], row['university'], row['total_experience'],
                row['research_publications'], row['is_class_teacher'], row['class_teacher_of'],
                row['subjects'], row['office_hours'], row['office_location'],
                row['training_courses'], row['conferences_attended'], row['awards'],
                row['date_of_birth'], row['gender'], row['blood_group'], row['marital_status'],
                row['personal_email'], row['personal_phone'], row['emergency_contact_name'],
                row['emergency_contact_phone'], row['emergency_contact_relation'],
                row['joining_date'], row['bank_name'], row['bank_account'], row['ifsc_code'],
                row['pan_number'], row['aadhaar_number']
            ]
            
            for col, value in enumerate(data):
                fmt = date_format if col in [19, 28] else None
                worksheet.write(1, col, value, fmt)

            worksheet.set_column('A:AH', 20)

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

    def export_pdf(self, row, filename, faculty, organization, qr_code_img):
        context = {
            "faculty": row,
            "photo": getattr(faculty.staff.photo, 'url', None) if faculty.staff.photo else None,
            "full_name": faculty.staff.user.get_full_name(),
            "organization": organization,
            "export_date": timezone.now(),
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": f"Faculty Detail - {faculty.staff.employee_id}",
            "qr_code": qr_code_img,
        }
        pdf_bytes = render_to_pdf("hr/export/faculty_detail_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)