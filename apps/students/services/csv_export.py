# students/services/csv_export.py
import csv
from io import StringIO
from django.http import HttpResponse
from django.utils import timezone

class StudentCSVExporter:
    @staticmethod
    def export_students(students, columns):
        """Export students to CSV with selected columns"""
        buffer = StringIO()
        writer = csv.writer(buffer)
        
        # Write header
        writer.writerow([col.replace("_", " ").title() for col in columns])
        
        # Write data rows
        for student in students:
            row = StudentCSVExporter._prepare_student_row(student, columns)
            writer.writerow([row.get(col, "") for col in columns])
        
        return buffer.getvalue()

    @staticmethod
    def _prepare_student_row(student, columns):
        """Prepare a dictionary of student data for the selected columns"""
        row = {}
        
        if "admission_number" in columns:
            row["admission_number"] = student.admission_number
        if "first_name" in columns:
            row["first_name"] = student.first_name
        if "last_name" in columns:
            row["last_name"] = student.last_name
        if "current_class" in columns:
            row["current_class"] = student.current_class.name if student.current_class else "-"
        if "section" in columns:
            row["section"] = student.section.name if student.section else "-"
        if "academic_year" in columns:
            row["academic_year"] = student.academic_year.name if student.academic_year else "-"
        if "status" in columns:
            row["status"] = student.get_status_display()
        if "email" in columns:
            row["email"] = student.email or "-"
        if "mobile" in columns:
            row["mobile"] = student.mobile or "-"
        if "date_of_birth" in columns:
            row["date_of_birth"] = student.date_of_birth.strftime("%b %d, %Y") if student.date_of_birth else "-"
        if "created_at" in columns:
            row["created_at"] = student.created_at.strftime("%b %d, %Y") if student.created_at else "-"
        if "gender" in columns:
            row["gender"] = student.get_gender_display()
        if "blood_group" in columns:
            row["blood_group"] = student.blood_group or "-"
        if "admission_type" in columns:
            row["admission_type"] = student.get_admission_type_display()
        if "caste" in columns:
            row["category"] = student.category or "-"
        if "religion" in columns:
            row["religion"] = student.religion or "-"
        if "has_hostel" in columns:
            row["has_hostel"] = "Yes" if hasattr(student, 'hostel') and student.hostel else "No"
        if "has_disability" in columns:
            row["has_disability"] = "Yes" if hasattr(student, 'medical_info') and student.medical_info.disability else "No"
        if "has_transport" in columns:
            row["has_transport"] = "Yes" if hasattr(student, 'transport') and student.transport else "No"
            
        return row