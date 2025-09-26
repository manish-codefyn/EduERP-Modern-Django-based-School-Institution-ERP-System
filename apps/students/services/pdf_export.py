# students/services/pdf_export.py
from django.utils import timezone
from utils.utils import render_to_pdf, export_pdf_response

class StudentPDFExporter:
    @staticmethod
    def export_students_list(students, columns, organization, filter_info):
        """Export students list to PDF"""
        # Prepare student data for PDF
        student_rows = []
        for student in students:
            row = StudentPDFExporter._prepare_student_row(student, columns)
            student_rows.append(row)
        
        context = {
            "columns": columns,
            "students": student_rows,
            "generated_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization else None,
            "filter_info": filter_info,
        }

        return render_to_pdf("students/export_students_list_pdf.html", context)

    @staticmethod
    def export_student_detail(student, organization):
        """Export individual student detail to PDF"""
        from utils.utils import qr_generate
        
        # QR Code Data
        qr_data = {
            "Admission No": student.admission_number,
            "Name": student.full_name,
            "Class": student.current_class.name if student.current_class else "",
            "Section": student.section.name if student.section else "",
            "Academic Year": student.academic_year.name if student.academic_year else "",
            "Updated": student.updated_at.strftime("%Y-%m-%d %H:%M"),
        }
        qr_code_img = qr_generate(qr_data, size=2, version=2, border=0)

        # Get student photo document (if any)
        photo_doc = student.documents.filter(doc_type="PHOTO").first()
        photo_url = photo_doc.file.url if photo_doc and photo_doc.file else None

        context = {
            "student": student,
            "photo": photo_url,
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization else None,
            "qr_code": qr_code_img,
            "export_date": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        return render_to_pdf("students/student_detail_pdf.html", context)

    @staticmethod
    def _prepare_student_row(student, columns):
        """Prepare student data for PDF export (same as CSV)"""
        # Reuse the same logic as CSV export
        from .csv_export import StudentCSVExporter
        return StudentCSVExporter._prepare_student_row(student, columns)