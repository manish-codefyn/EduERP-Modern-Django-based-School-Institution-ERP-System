# attendance/views.py
import csv
from io import StringIO
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

from .models import Attendance
from apps.students.models import Student
from apps.academics.models import Class, Section
from utils.utils import render_to_pdf, export_pdf_response,qr_generate
from apps.organization.models import Institution
from apps.core.utils import get_user_institution


class AttendanceExportDetailView(View):
    """
    Export detailed attendance data for a specific student (id wise).
    Supports CSV and PDF.
    """
    def get(self, request, pk, *args, **kwargs):
        fmt = request.GET.get("format", "pdf").lower()
        
        # Get attendance record by ID with institution check
        attendance = get_object_or_404(
            Attendance.objects.select_related(
                'student', 'student__current_class', 
                'student__section', 'marked_by', 'institution'
            ),
            id=pk,
            student__institution=request.user.profile.institution
        )

        # Build filename
        filename = f"Attendance_{attendance.student.roll_number}_{attendance.date}"

        # Prepare attendance data for export
        attendance_data = {
            "roll_number": attendance.student.roll_number,
            "student_name": attendance.student.full_name,
            "class_name": str(attendance.student.current_class),
            "section": str(attendance.student.section) if attendance.student.section else "N/A",
            "date": attendance.date.strftime("%Y-%m-%d"),
            "status": attendance.get_status_display(),
            "status_code": attendance.status,
            "remarks": attendance.remarks or "No remarks",
            "marked_by": attendance.marked_by.get_full_name(),
            "institution": attendance.institution.name,
            "created_at": attendance.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": attendance.updated_at.strftime("%Y-%m-%d %H:%M"),
        }

        # CSV Export
        if fmt == "csv":
            buffer = StringIO()
            writer = csv.writer(buffer)
            
            # Create headers and data
            headers = ["Field", "Value"]
            writer.writerow(headers)
            
            for key, value in attendance_data.items():
                field_name = key.replace('_', ' ').title()
                writer.writerow([field_name, value])
                
            resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
            return resp

        # PDF Export (default)
        elif fmt == "pdf":
            context = {
                "attendance": attendance_data,
                "generated_date": timezone.now(),
                "organization": request.user.profile.institution,
                "logo": getattr(request.user.profile.institution.logo, 'url', None) if request.user.profile.institution else None,
                "stamp": getattr(request.user.profile.institution.stamp, 'url', None) if request.user.profile.institution else None,
            }
            pdf_bytes = render_to_pdf("attendance/export/attendance_detail_pdf.html", context)
            if pdf_bytes:
                return export_pdf_response(pdf_bytes, f"{filename}.pdf")
            return HttpResponse("Error generating PDF", status=500)

        # Excel Export
        elif fmt == "excel":
            buffer = StringIO()
            writer = csv.writer(buffer)
            
            headers = ["Field", "Value"]
            writer.writerow(headers)
            
            for key, value in attendance_data.items():
                field_name = key.replace('_', ' ').title()
                writer.writerow([field_name, value])
                
            resp = HttpResponse(buffer.getvalue(), content_type="application/vnd.ms-excel")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.xls"'
            return resp

        return HttpResponse("Invalid export format", status=400)



class AttendanceExportView(LoginRequiredMixin, View):
    """
    Export Attendance data with filters:
    - class_id, section_id
    - start_date, end_date
    - status (PRESENT, ABSENT, HALF_DAY)
    - student_id, roll_number
    - Only for students in the user's institution
    """

    def get(self, request, *args, **kwargs):
        fmt = request.GET.get("format", "csv").lower()
        class_id = request.GET.get("class_id")
        section_id = request.GET.get("section_id")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        status = request.GET.get("status")
        student_id = request.GET.get("student_id")
        roll_number = request.GET.get("roll_number")

        # Base queryset filtered by student's institution
        attendance_qs = Attendance.objects.select_related(
            'student', 'student__current_class', 'student__section'
        ).filter(student__institution=request.user.profile.institution)

        # Apply filters
        filters = Q()

        if class_id:
            filters &= Q(student__current_class_id=class_id)
            class_obj = get_object_or_404(Class, id=class_id)
        else:
            class_obj = None

        if section_id:
            filters &= Q(student__section_id=section_id)
            section_obj = get_object_or_404(Section, id=section_id)
        else:
            section_obj = None

        if start_date and end_date:
            filters &= Q(date__range=[start_date, end_date])
        elif start_date:
            filters &= Q(date__gte=start_date)
        elif end_date:
            filters &= Q(date__lte=end_date)

        if status:
            filters &= Q(status=status)

        if student_id:
            filters &= Q(student_id=student_id)

        if roll_number:
            filters &= Q(student__roll_number=roll_number)

        attendance_qs = attendance_qs.filter(filters).order_by('student__roll_number', 'date')

        # Build filename
        filename_parts = ["attendance"]
        if class_obj:
            filename_parts.append(f"Class_{class_obj.name}")
        if section_obj:
            filename_parts.append(f"Section_{section_obj.name}")
        if start_date:
            filename_parts.append(f"From_{start_date}")
        if end_date:
            filename_parts.append(f"To_{end_date}")
        if status:
            filename_parts.append(f"Status_{status}")
        if student_id:
            filename_parts.append(f"Student_{student_id}")
        if roll_number:
            filename_parts.append(f"Roll_{roll_number}")

        filename = "_".join(filename_parts)

        # Build data rows - use keys without spaces for template compatibility
        rows = []
        for att in attendance_qs:
            rows.append({
                "roll_no": att.student.roll_number,
                "name": att.student.full_name,
                "class_name": str(att.student.current_class),
                "section": str(att.student.section),
                "date": att.date.strftime("%Y-%m-%d"),
                "status": att.get_status_display(),
                "remarks": att.remarks or "",
            })

        # CSV Export
        if fmt == "csv":
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["Roll No", "Name", "Class", "Section", "Date", "Status", "Remarks"])
            for r in rows:
                writer.writerow([
                    r["roll_no"], r["name"], r["class_name"],
                    r["section"], r["date"], r["status"], r["remarks"]
                ])
            resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
            return resp

        # PDF Export
        elif fmt == "pdf":
            organization = request.user.profile.institution  # assuming org stored in user profile
            context = {
                "attendance_data": rows,
                "generated_date": timezone.now(),
                "class_obj": class_obj,
                "section_obj": section_obj,
                "status_filter": status,
                "start_date": start_date,
                "end_date": end_date,
                "student_id": student_id,
                "roll_number": roll_number,
                "organization": organization,
                "logo": getattr(organization.logo, 'url', None) if organization else None,
                "stamp": getattr(organization.stamp, 'url', None) if organization else None,
            }
            pdf_bytes = render_to_pdf("attendance/export/attendance_pdf.html", context)
            if pdf_bytes:
                return export_pdf_response(pdf_bytes, f"{filename}.pdf")
            return HttpResponse("Error generating PDF", status=500)

        return HttpResponse("Invalid export format", status=400)



def load_sections(request):
    """
    AJAX view to load sections based on selected class
    """
    class_id = request.GET.get('class_id')
    if class_id:
        sections = Section.objects.filter(class_name_id=class_id).order_by('name')
        return JsonResponse(list(sections.values('id', 'name')), safe=False)
    return JsonResponse([], safe=False)


def load_students(request):
    """
    AJAX view to load students based on selected class and section
    """
    class_id = request.GET.get('class_id')
    section_id = request.GET.get('section_id')
    
    students = Student.objects.all()
    
    if class_id:
        students = students.filter(current_class_id=class_id)
    
    if section_id:
        students = students.filter(section_id=section_id)
        
    students = students.order_by('roll_number')
    
    return JsonResponse(list(students.values('id', 'first_name', 'roll_number')), safe=False)