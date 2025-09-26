from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import messages
from io import StringIO
import csv

from apps.core.mixins import DirectorRequiredMixin,StaffManagementRequiredMixin
from .models import Student
from apps.academics.models import Class,Section
from apps.core.utils import get_user_institution

from utils.utils import render_to_pdf, export_pdf_response, qr_generate

class StudentExportDetailView(StaffManagementRequiredMixin, View):
    """
    Export detailed student data for a specific student (id wise).
    Supports CSV, PDF, and Excel.
    """

    def get(self, request, pk, *args, **kwargs):
        fmt = request.GET.get("format", "pdf").lower()
        
        # Get student record
        student = get_object_or_404(
            Student.objects.select_related('institution', 'current_class', 'section', 'academic_year'),
            id=pk,
            institution=get_user_institution(request.user)
        )

        filename = f"Student_{student.admission_number}_{student.full_name}"

        # Prepare student data
        student_data = {
            "admission_number": student.admission_number,
            "full_name": student.full_name,
            "email": student.email,
            "mobile": student.mobile,
            "date_of_birth": student.date_of_birth.strftime("%Y-%m-%d") if student.date_of_birth else "N/A",
            "gender": student.get_gender_display(),
            "blood_group": student.blood_group or "N/A",
            "category": student.get_category_display() if student.category else "N/A",
            "religion": student.get_religion_display() if student.religion else "N/A",
            "roll_number": student.roll_number or "N/A",
            "enrollment_date": student.enrollment_date.strftime("%Y-%m-%d") if student.enrollment_date else "N/A",
            "admission_type": student.get_admission_type_display(),
            "academic_year": str(student.academic_year) if student.academic_year else "N/A",
            "current_class": str(student.current_class) if student.current_class else "N/A",
            "section": str(student.section) if student.section else "N/A",
            "age": student.age,
            "status": student.get_status_display(),
            "permanent_address": student.permanent_address or "N/A",
            "current_address": student.current_address or "N/A",
            "fee_status": student.fee_status,
            "institution": student.institution.name if student.institution else "N/A",
            "created_at": student.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": student.updated_at.strftime("%Y-%m-%d %H:%M"),
        }

        # Get guardian information
        guardians = student.guardians.all()
        guardian_data = []
        for i, guardian in enumerate(guardians, 1):
            guardian_data.append({
                f"guardian_{i}_name": guardian.name,
                f"guardian_{i}_relation": guardian.get_relation_display(),
                f"guardian_{i}_occupation": guardian.get_occupation_display() if guardian.occupation else "N/A",
                f"guardian_{i}_phone": guardian.phone or "N/A",
                f"guardian_{i}_email": guardian.email or "N/A",
                f"guardian_{i}_address": guardian.address or "N/A",
            })
        
        # Merge guardian data into student data
        for g_data in guardian_data:
            student_data.update(g_data)

        # Get medical information
        medical_info = getattr(student, 'medical_info', None)
        if medical_info:
            student_data.update({
                "medical_conditions": medical_info.conditions or "N/A",
                "allergies": medical_info.allergies or "N/A",
                "disability": "Yes" if medical_info.disability else "No",
                "disability_type": medical_info.disability_type or "N/A",
                "disability_percentage": medical_info.disability_percentage or "N/A",
                "emergency_contact_name": medical_info.emergency_contact_name or "N/A",
                "emergency_contact_phone": medical_info.emergency_contact_phone or "N/A",
                "emergency_contact_relation": medical_info.emergency_contact_relation or "N/A",
            })
        else:
            student_data.update({
                "medical_conditions": "N/A",
                "allergies": "N/A",
                "disability": "N/A",
                "disability_type": "N/A",
                "disability_percentage": "N/A",
                "emergency_contact_name": "N/A",
                "emergency_contact_phone": "N/A",
                "emergency_contact_relation": "N/A",
            })

        # Generate QR code (for student profile link or admission number)
        qr_data = request.build_absolute_uri(student.get_absolute_url())  # link to student profile
        qr_img = qr_generate(qr_data)  # this should return a PIL Image or BytesIO

        # CSV Export
        if fmt == "csv":
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["Field", "Value"])
            for key, value in student_data.items():
                writer.writerow([key.replace('_', ' ').title(), value])
            resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
            return resp

        # PDF Export
        elif fmt == "pdf":
            context = {
                "student": student_data,
                "student_obj": student,
                "generated_date": timezone.now(),
                "organization": student.institution,
                "logo": getattr(student.institution.logo, 'url', None) if student.institution else None,
                "stamp": getattr(student.institution.stamp, 'url', None) if student.institution else None,
                "photo": getattr(student.get_photo().file, 'url', None) if student.get_photo() else None,
                "qr_code": qr_img,  # pass the QR code to template
            }
            pdf_bytes = render_to_pdf("students/export/student_detail_pdf.html", context)
            if pdf_bytes:
                return export_pdf_response(pdf_bytes, f"{filename}.pdf")
            return HttpResponse("Error generating PDF", status=500)

        # Excel Export
        elif fmt == "excel":
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["Field", "Value"])
            for key, value in student_data.items():
                writer.writerow([key.replace('_', ' ').title(), value])
            resp = HttpResponse(buffer.getvalue(), content_type="application/vnd.ms-excel")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.xls"'
            return resp

        return HttpResponse("Invalid export format", status=400)



class StudentExportView(StaffManagementRequiredMixin, View):
    """
    Export Student data with filters:
    - class
    - section
    - status (active/inactive)
    - gender
    - category
    - religion
    - admission_type
    - search query
    - Only for students in the user's institution
    """

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        student_class = request.GET.get("class")
        section = request.GET.get("section")
        status = request.GET.get("status")
        gender = request.GET.get("gender")
        category = request.GET.get("category")
        religion = request.GET.get("religion")
        admission_type = request.GET.get("admission_type")
        search_query = request.GET.get("search")

        # Base queryset filtered by institution
        student_qs = Student.objects.select_related(
            'institution', 'current_class', 'section', 'academic_year'
        ).filter(
            institution=get_user_institution(request.user)
        )

        # Apply filters
        filters = Q()

        if student_class:
            filters &= Q(current_class_id=student_class)

        if section:
            filters &= Q(section_id=section)

        if status:
            filters &= Q(status=status)

        if gender:
            filters &= Q(gender=gender)

        if category:
            filters &= Q(category=category)

        if religion:
            filters &= Q(religion=religion)

        if admission_type:
            filters &= Q(admission_type=admission_type)

        if search_query:
            filters &= (
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(admission_number__icontains=search_query) |
                Q(roll_number__icontains=search_query) |
                Q(mobile__icontains=search_query)
            )

        student_qs = student_qs.filter(filters).distinct().order_by('first_name', 'last_name')

        # Summary info
        total_count = student_qs.count()
        active_count = student_qs.filter(status="ACTIVE").count()
        export_date = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build filename
        filename_parts = ["students"]
        if student_class:
            class_obj = Class.objects.filter(id=student_class).first()
            if class_obj:
                filename_parts.append(f"Class_{class_obj.name}")
        if section:
            section_obj = Section.objects.filter(id=section).first()
            if section_obj:
                filename_parts.append(f"Section_{section_obj.name}")
        if status:
            filename_parts.append(f"Status_{status}")
        if gender:
            filename_parts.append(f"Gender_{gender}")
        if category:
            filename_parts.append(f"Category_{category}")
        if religion:
            filename_parts.append(f"Religion_{religion}")
        if admission_type:
            filename_parts.append(f"AdmissionType_{admission_type}")
        if search_query:
            filename_parts.append(f"Search_{search_query}")

        filename = "_".join(filename_parts)

        # Build data rows
        rows = []
        for student in student_qs:
            rows.append({
                "admission_number": student.admission_number,
                "full_name": student.full_name,
                "email": student.email,
                "mobile": student.mobile,
                "date_of_birth": student.date_of_birth.strftime("%Y-%m-%d") if student.date_of_birth else "N/A",
                "gender": student.get_gender_display(),
                "blood_group": student.blood_group or "N/A",
                "category": student.get_category_display() if student.category else "N/A",
                "religion": student.get_religion_display() if student.religion else "N/A",
                "roll_number": student.roll_number or "N/A",
                "enrollment_date": student.enrollment_date.strftime("%Y-%m-%d") if student.enrollment_date else "N/A",
                "admission_type": student.get_admission_type_display(),
                "academic_year": str(student.academic_year) if student.academic_year else "N/A",
                "current_class": str(student.current_class) if student.current_class else "N/A",
                "section": str(student.section) if student.section else "N/A",
                "age": student.age,
                "status": student.get_status_display(),
                "fee_status": student.fee_status,
            })

        # CSV Export
        if fmt == "csv":
            buffer = StringIO()
            writer = csv.writer(buffer)
            # Add summary at top
            writer.writerow([f"Total Students: {total_count}", f"Active Students: {active_count}", f"Report Generated: {export_date}"])
            writer.writerow([])  # Empty row
            writer.writerow([
                "Admission Number", "Full Name", "Email", "Mobile", "Date of Birth",
                "Gender", "Blood Group", "Category", "Religion", "Roll Number",
                "Enrollment Date", "Admission Type", "Academic Year", "Class",
                "Section", "Age", "Status", "Fee Status"
            ])
            for r in rows:
                writer.writerow([
                    r["admission_number"], r["full_name"], r["email"], r["mobile"],
                    r["date_of_birth"], r["gender"], r["blood_group"], r["category"],
                    r["religion"], r["roll_number"], r["enrollment_date"],
                    r["admission_type"], r["academic_year"], r["current_class"],
                    r["section"], r["age"], r["status"], r["fee_status"]
                ])
            resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
            return resp

        # PDF Export
        elif fmt == "pdf":
            organization = get_user_institution(request.user)
            context = {
                "students": rows,
                "total_count": total_count,
                "active_count": active_count,
                "export_date": export_date,
                "generated_date": timezone.now(),
                "class_filter": student_class,
                "section_filter": section,
                "status_filter": status,
                "gender_filter": gender,
                "category_filter": category,
                "religion_filter": religion,
                "admission_type_filter": admission_type,
                "search_query": search_query,
                "organization": organization,
                "logo": getattr(organization.logo, 'url', None) if organization else None,
                "stamp": getattr(organization.stamp, 'url', None) if organization else None,
            }
            pdf_bytes = render_to_pdf("students/export/students_pdf.html", context)
            if pdf_bytes:
                return export_pdf_response(pdf_bytes, f"{filename}.pdf")
            return HttpResponse("Error generating PDF", status=500)

        # Excel Export
        elif fmt == "excel":
            buffer = StringIO()
            writer = csv.writer(buffer)
            # Add summary at top
            writer.writerow([f"Total Students: {total_count}", f"Active Students: {active_count}", f"Report Generated: {export_date}"])
            writer.writerow([])  # Empty row
            writer.writerow([
                "Admission Number", "Full Name", "Email", "Mobile", "Date of Birth",
                "Gender", "Blood Group", "Category", "Religion", "Roll Number",
                "Enrollment Date", "Admission Type", "Academic Year", "Class",
                "Section", "Age", "Status", "Fee Status"
            ])
            for r in rows:
                writer.writerow([
                    r["admission_number"], r["full_name"], r["email"], r["mobile"],
                    r["date_of_birth"], r["gender"], r["blood_group"], r["category"],
                    r["religion"], r["roll_number"], r["enrollment_date"],
                    r["admission_type"], r["academic_year"], r["current_class"],
                    r["section"], r["age"], r["status"], r["fee_status"]
                ])
            resp = HttpResponse(buffer.getvalue(), content_type="application/vnd.ms-excel")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.xls"'
            return resp

        return HttpResponse("Invalid export format", status=400)