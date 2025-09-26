# students/views/export_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import View
from django.contrib import messages
from django.utils import timezone
from .models import Student
from apps.organization.models import Institution
from .services.csv_export import StudentCSVExporter
from .services.pdf_export import StudentPDFExporter
from .services.filter_service import StudentFilterService
from utils.utils import render_to_pdf,export_pdf_response


class ExportStudentsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Main export view that handles both CSV and PDF exports"""
    permission_required = "students.view_student"
    
    def get(self, request):
        fmt = request.GET.get("format", "csv").lower()
        
        # Get selected columns
        columns = request.GET.getlist("columns")
        if not columns:
            columns_param = request.GET.get("columns", "")
            if columns_param:
                columns = [c.strip() for c in columns_param.split(",") if c.strip()]

        # Default fields if none selected
        if not columns:
            columns = [
                "admission_number", "first_name", "last_name", "current_class",
                "section", "academic_year", "status", "email", "mobile",
                "date_of_birth", "created_at"
            ]

        # Apply filters and get students
        students = StudentFilterService.filter_students(request.GET)
        filter_info = StudentFilterService.get_filter_info(request.GET)
        organization = Institution.objects.first()

        # Handle CSV export
        if fmt == "csv":
            csv_data = StudentCSVExporter.export_students(students, columns)
            resp = HttpResponse(csv_data, content_type="text/csv")
            resp["Content-Disposition"] = 'attachment; filename="students.csv"'
            return resp

        # Handle PDF export
        if fmt == "pdf":
            pdf_data = StudentPDFExporter.export_students_list(students, columns, organization, filter_info)
            
            if pdf_data:
                # Create descriptive filename
                filename_parts = ["students"]
                if filter_info["class_filter"]:
                    filename_parts.append(filter_info["class_filter"].name.replace(" ", "_"))
                if filter_info["section_filter"]:
                    filename_parts.append(filter_info["section_filter"].name.replace(" ", "_"))
                if filter_info["status_filter"]:
                    filename_parts.append(filter_info["status_filter"].replace(" ", "_"))
                
                filename = f"{'_'.join(filename_parts)}.pdf" if len(filename_parts) > 1 else "students.pdf"
                
                return export_pdf_response(pdf_data, filename)
            
            messages.error(request, "Error generating PDF")
            return redirect('students:student_list')

        return HttpResponse("Invalid export format", status=400)


class ExportStudentDetailPDFView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Export individual student detail as PDF"""
    permission_required = "students.view_student"
    
    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        organization = Institution.objects.first()
        
        pdf_data = StudentPDFExporter.export_student_detail(student, organization)
        
        if pdf_data:
            filename = f"student_{student.admission_number}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            return export_pdf_response(pdf_data, filename)
        
        messages.error(request, "Error generating PDF")
        return redirect("students:student_detail", pk=student.pk)