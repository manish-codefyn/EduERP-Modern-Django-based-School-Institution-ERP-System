# students/services/filter_service.py
from django.db.models import Q
from apps.students.models import Student


class StudentFilterService:
    @staticmethod
    def filter_students(request_get_params):
        """Apply filters to student queryset based on request parameters"""
        queryset = Student.objects.select_related(
            "current_class", "section", "academic_year"
        ).prefetch_related('medical_info', 'transport', 'hostel').all()

        # Apply filters
        class_id = request_get_params.get("class_id")
        if class_id:
            queryset = queryset.filter(current_class_id=class_id)

        section_id = request_get_params.get("section_id")
        if section_id:
            queryset = queryset.filter(section_id=section_id)

        status = request_get_params.get("status")
        if status:
            queryset = queryset.filter(status=status)

        gender = request_get_params.get("gender")
        if gender:
            queryset = queryset.filter(gender=gender)

        blood_group = request_get_params.get("blood_group")
        if blood_group:
            queryset = queryset.filter(blood_group=blood_group)

        admission_type = request_get_params.get("admission_type")
        if admission_type:
            queryset = queryset.filter(admission_type=admission_type)

        # Additional filters
        has_hostel = request_get_params.get("has_hostel")
        if has_hostel:
            if has_hostel == "yes":
                queryset = queryset.filter(hostel__isnull=False)
            elif has_hostel == "no":
                queryset = queryset.filter(hostel__isnull=True)

        has_disability = request_get_params.get("has_disability")
        if has_disability:
            if has_disability == "yes":
                queryset = queryset.filter(medical_info__disability=True)
            elif has_disability == "no":
                queryset = queryset.filter(medical_info__disability=False)

        caste = request_get_params.get("caste")
        if caste:
            queryset = queryset.filter(caste__iexact=caste)

        religion = request_get_params.get("religion")
        if religion:
            queryset = queryset.filter(religion__iexact=religion)

        has_transport = request_get_params.get("has_transport")
        if has_transport:
            if has_transport == "yes":
                queryset = queryset.filter(transport__isnull=False)
            elif has_transport == "no":
                queryset = queryset.filter(transport__isnull=True)

        # Order the results
        return queryset.order_by("first_name", "last_name")

    @staticmethod
    def get_filter_info(request_get_params):
        """Get information about applied filters for display"""
        from apps.academics.models import Class, Section
        from apps.students.models import Student
        
        class_id = request_get_params.get("class_id")
        section_id = request_get_params.get("section_id")
        status = request_get_params.get("status")
        gender = request_get_params.get("gender")
        blood_group = request_get_params.get("blood_group")
        admission_type = request_get_params.get("admission_type")
        has_hostel = request_get_params.get("has_hostel")
        has_disability = request_get_params.get("has_disability")
        caste = request_get_params.get("caste")
        religion = request_get_params.get("religion")
        has_transport = request_get_params.get("has_transport")

        return {
            "class_filter": Class.objects.filter(id=class_id).first() if class_id else None,
            "section_filter": Section.objects.filter(id=section_id).first() if section_id else None,
            "status_filter": dict(Student.STATUS_CHOICES).get(status) if status else None,
            "gender_filter": dict(Student.GENDER_CHOICES).get(gender) if gender else None,
            "blood_group_filter": dict(Student.BLOOD_GROUP_CHOICES).get(blood_group) if blood_group else None,
            "admission_type_filter": dict(Student.ADMISSION_TYPE_CHOICES).get(admission_type) if admission_type else None,
            "hostel_filter": "Yes" if has_hostel == "yes" else "No" if has_hostel == "no" else None,
            "disability_filter": "Yes" if has_disability == "yes" else "No" if has_disability == "no" else None,
            "caste_filter": caste if caste else None,
            "religion_filter": religion if religion else None,
            "transport_filter": "Yes" if has_transport == "yes" else "No" if has_transport == "no" else None,
        }