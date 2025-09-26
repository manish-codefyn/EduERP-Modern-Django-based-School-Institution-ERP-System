from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import messages
from io import StringIO
import csv

from apps.core.mixins import DirectorRequiredMixin
from .models import Teacher
from apps.core.utils import get_user_institution

from utils.utils import render_to_pdf, export_pdf_response, qr_generate

class TeacherExportDetailView(DirectorRequiredMixin, View):
    """
    Export detailed teacher data for a specific teacher (id wise).
    Supports CSV, PDF, and Excel.
    """

    def get(self, request, pk, *args, **kwargs):
        fmt = request.GET.get("format", "pdf").lower()
        
        # Get teacher record
        teacher = get_object_or_404(
            Teacher.objects.select_related('institution'),
            id=pk,
            institution=get_user_institution(request.user)
        )

        filename = f"Teacher_{teacher.employee_id}_{teacher.get_full_name()}"

        # Prepare teacher data
        teacher_data = {
            "employee_id": teacher.employee_id,
            "full_name": teacher.get_full_name(),
            "email": teacher.email,
            "mobile": teacher.mobile or "N/A",
            "date_of_birth": teacher.dob.strftime("%Y-%m-%d") if teacher.dob else "N/A",
            "gender": teacher.get_gender_display(),
            "blood_group": teacher.blood_group or "N/A",
            "qualification": teacher.get_qualification_display(),
            "specialization": teacher.specialization or "N/A",
            "subjects_taught": teacher.get_subjects_list(),
            "organization_type": teacher.get_organization_type_display(),
            "department": teacher.get_department_display() if teacher.department else "N/A",
            "designation": teacher.get_designation_display(),
            "faculty_type": teacher.get_faculty_type_display(),
            "is_class_teacher": "Yes" if teacher.is_class_teacher else "No",
            "class_teacher_of": str(teacher.class_teacher_of) if teacher.class_teacher_of else "N/A",
            "teaching_grade_levels": teacher.teaching_grade_levels or "N/A",
            "date_of_joining": teacher.joining_date.strftime("%Y-%m-%d") if teacher.joining_date else "N/A",
            "experience": f"{teacher.get_teaching_experience()} years",
            "salary": str(teacher.salary) if teacher.salary else "N/A",
            "address": teacher.address or "N/A",
            "emergency_contact": f"{teacher.emergency_contact} ({teacher.emergency_contact_name})" if teacher.emergency_contact_name else teacher.emergency_contact,
            "status": "Active" if teacher.is_active else "Inactive",
            "institution": teacher.institution.name,
            "created_at": teacher.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": teacher.updated_at.strftime("%Y-%m-%d %H:%M"),
        }

        # Generate QR code (for teacher profile link or employee ID)
        qr_data = request.build_absolute_uri(teacher.get_absolute_url())  # link to teacher profile
        qr_img = qr_generate(qr_data)  # this should return a PIL Image or BytesIO

        # CSV Export
        if fmt == "csv":
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["Field", "Value"])
            for key, value in teacher_data.items():
                writer.writerow([key.replace('_', ' ').title(), value])
            resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
            return resp

        # PDF Export
        elif fmt == "pdf":
            context = {
                "teacher": teacher_data,
                "teacher_obj": teacher,
                "generated_date": timezone.now(),
                "organization": teacher.institution,
                "logo": getattr(teacher.institution.logo, 'url', None) if teacher.institution else None,
                "stamp": getattr(teacher.institution.stamp, 'url', None) if teacher.institution else None,
                "photo": getattr(teacher.photo, 'url', None) if teacher.photo else None,
                "qr_code": qr_img,  # pass the QR code to template
            }
            pdf_bytes = render_to_pdf("teachers/export/teacher_detail_pdf.html", context)
            if pdf_bytes:
                return export_pdf_response(pdf_bytes, f"{filename}.pdf")
            return HttpResponse("Error generating PDF", status=500)

        # Excel Export
        elif fmt == "excel":
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["Field", "Value"])
            for key, value in teacher_data.items():
                writer.writerow([key.replace('_', ' ').title(), value])
            resp = HttpResponse(buffer.getvalue(), content_type="application/vnd.ms-excel")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.xls"'
            return resp

        return HttpResponse("Invalid export format", status=400)


class TeacherExportView(DirectorRequiredMixin, View):
    """
    Export Teacher data with filters:
    - organization_type
    - department
    - designation
    - faculty_type
    - is_class_teacher
    - status (active/inactive)
    - search query
    - Only for teachers in the user's institution
    """

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        organization_type = request.GET.get("organization_type")
        department = request.GET.get("department")
        designation = request.GET.get("designation")
        faculty_type = request.GET.get("faculty_type")
        is_class_teacher = request.GET.get("is_class_teacher")
        status = request.GET.get("status")
        search_query = request.GET.get("search")

        # Base queryset filtered by institution
        teacher_qs = Teacher.objects.select_related('institution').filter(
            institution=get_user_institution(request.user)
        )

        # Apply filters
        filters = Q()

        if organization_type:
            filters &= Q(organization_type=organization_type)

        if department:
            filters &= Q(department=department)

        if designation:
            filters &= Q(designation=designation)

        if faculty_type:
            filters &= Q(faculty_type=faculty_type)

        if is_class_teacher:
            if is_class_teacher.lower() == 'true':
                filters &= Q(is_class_teacher=True)
            elif is_class_teacher.lower() == 'false':
                filters &= Q(is_class_teacher=False)

        if status:
            if status.lower() == 'active':
                filters &= Q(is_active=True)
            elif status.lower() == 'inactive':
                filters &= Q(is_active=False)

        if search_query:
            filters &= (
                Q(first_name__icontains=search_query) |
                Q(middle_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(employee_id__icontains=search_query) |
                Q(qualification__icontains=search_query) |
                Q(specialization__icontains=search_query) |
                Q(subjects__name__icontains=search_query)
            )

        teacher_qs = teacher_qs.filter(filters).distinct().order_by('last_name', 'first_name')

        # Summary info
        total_count = teacher_qs.count()
        active_count = teacher_qs.filter(is_active=True).count()
        export_date = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build filename
        filename_parts = ["teachers"]
        if organization_type:
            filename_parts.append(f"OrgType_{organization_type}")
        if department:
            filename_parts.append(f"Dept_{department}")
        if designation:
            filename_parts.append(f"Desig_{designation}")
        if faculty_type:
            filename_parts.append(f"Faculty_{faculty_type}")
        if is_class_teacher:
            filename_parts.append(f"ClassTeacher_{is_class_teacher}")
        if status:
            filename_parts.append(f"Status_{status}")
        if search_query:
            filename_parts.append(f"Search_{search_query}")

        filename = "_".join(filename_parts)

        # Build data rows
        rows = []
        for teacher in teacher_qs:
            rows.append({
                "employee_id": teacher.employee_id,
                "full_name": teacher.get_full_name(),
                "email": teacher.email,
                "mobile": teacher.mobile or "N/A",
                "organization_type": teacher.get_organization_type_display(),
                "department": teacher.get_department_display() if teacher.department else "N/A",
                "designation": teacher.get_designation_display(),
                "qualification": teacher.get_qualification_display(),
                "specialization": teacher.specialization or "N/A",
                "subjects": teacher.get_subjects_list(),
                "is_class_teacher": "Yes" if teacher.is_class_teacher else "No",
                "class_teacher_of": str(teacher.class_teacher_of) if teacher.class_teacher_of else "N/A",
                "faculty_type": teacher.get_faculty_type_display(),
                "date_of_joining": teacher.joining_date.strftime("%Y-%m-%d") if teacher.joining_date else "N/A",
                "experience": f"{teacher.get_teaching_experience()} years",
                "salary": str(teacher.salary) if teacher.salary else "N/A",
                "status": "Active" if teacher.is_active else "Inactive",
            })

        # CSV Export
        if fmt == "csv":
            buffer = StringIO()
            writer = csv.writer(buffer)
            # Add summary at top
            writer.writerow([f"Total Teachers: {total_count}", f"Active Teachers: {active_count}", f"Report Generated: {export_date}"])
            writer.writerow([])  # Empty row
            writer.writerow([
                "Employee ID", "Full Name", "Email", "Mobile", "Organization Type",
                "Department", "Designation", "Qualification", "Specialization",
                "Subjects", "Is Class Teacher", "Class Teacher Of", "Faculty Type",
                "Date of Joining", "Experience", "Salary", "Status"
            ])
            for r in rows:
                writer.writerow([
                    r["employee_id"], r["full_name"], r["email"], r["mobile"],
                    r["organization_type"], r["department"], r["designation"],
                    r["qualification"], r["specialization"], r["subjects"],
                    r["is_class_teacher"], r["class_teacher_of"], r["faculty_type"],
                    r["date_of_joining"], r["experience"], r["salary"], r["status"]
                ])
            resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
            return resp

        # PDF Export
        elif fmt == "pdf":
            organization = get_user_institution(request.user)
            context = {
                "teachers_data": rows,
                "total_count": total_count,
                "active_count": active_count,
                "export_date": export_date,
                "generated_date": timezone.now(),
                "organization_type_filter": organization_type,
                "department_filter": department,
                "designation_filter": designation,
                "faculty_type_filter": faculty_type,
                "is_class_teacher_filter": is_class_teacher,
                "status_filter": status,
                "search_query": search_query,
                "organization": organization,
                "logo": getattr(organization.logo, 'url', None) if organization else None,
                "stamp": getattr(organization.stamp, 'url', None) if organization else None,
            }
            pdf_bytes = render_to_pdf("teachers/export/teachers_pdf.html", context)
            if pdf_bytes:
                return export_pdf_response(pdf_bytes, f"{filename}.pdf")
            return HttpResponse("Error generating PDF", status=500)

        # Excel Export
        elif fmt == "excel":
            buffer = StringIO()
            writer = csv.writer(buffer)
            # Add summary at top
            writer.writerow([f"Total Teachers: {total_count}", f"Active Teachers: {active_count}", f"Report Generated: {export_date}"])
            writer.writerow([])  # Empty row
            writer.writerow([
                "Employee ID", "Full Name", "Email", "Mobile", "Organization Type",
                "Department", "Designation", "Qualification", "Specialization",
                "Subjects", "Is Class Teacher", "Class Teacher Of", "Faculty Type",
                "Date of Joining", "Experience", "Salary", "Status"
            ])
            for r in rows:
                writer.writerow([
                    r["employee_id"], r["full_name"], r["email"], r["mobile"],
                    r["organization_type"], r["department"], r["designation"],
                    r["qualification"], r["specialization"], r["subjects"],
                    r["is_class_teacher"], r["class_teacher_of"], r["faculty_type"],
                    r["date_of_joining"], r["experience"], r["salary"], r["status"]
                ])
            resp = HttpResponse(buffer.getvalue(), content_type="application/vnd.ms-excel")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.xls"'
            return resp

        return HttpResponse("Invalid export format", status=400)


