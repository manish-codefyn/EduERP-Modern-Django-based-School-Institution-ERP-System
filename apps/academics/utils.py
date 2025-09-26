import logging
from django.utils import timezone
from django.db.models import Q

logger = logging.getLogger(__name__)

def get_current_academic_year():
    """Get the current academic year based on today's date"""
    try:
        from academics.models import AcademicYear
        today = timezone.now().date()
        
        # First try to get the explicitly marked current academic year
        current_year = AcademicYear.objects.filter(is_current=True).first()
        if current_year:
            return current_year
            
        # Fallback: find academic year that contains today's date
        current_year = AcademicYear.objects.filter(
            start_date__lte=today,
            end_date__gte=today
        ).first()
        
        return current_year
        
    except ImportError:
        return None

def validate_enrollment_date(enrollment_date, academic_year):
    """Validate that enrollment date is within academic year range"""
    if not enrollment_date or not academic_year:
        return True
        
    if enrollment_date < academic_year.start_date:
        return False, _('Enrollment date cannot be before academic year start')
        
    if enrollment_date > academic_year.end_date:
        return False, _('Enrollment date cannot be after academic year end')
        
    return True, None