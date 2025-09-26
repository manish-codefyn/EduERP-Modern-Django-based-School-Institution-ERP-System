# hr/views.py

import json
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

# Import all your HR models
from .models import Staff, Department, LeaveApplication, HrAttendance, Designation, Faculty, LeaveBalance, LeaveType, Payroll

class HRDashboardView(LoginRequiredMixin, TemplateView):
    """
    A class-based view to display the main HR dashboard with statistics and charts.
    """
    template_name = 'hr/hr_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # We assume a single institution context for this dashboard.
        # In a real multi-tenant app, you'd filter by the logged-in user's institution.
        # For this example, we'll just use the first institution found if any.
        
        # --- 1. Key Statistic Cards ---
        today = timezone.now().date()
        context['total_staff'] = Staff.objects.filter(is_active=True).count()
        context['total_departments'] = Department.objects.filter(is_active=True).count()
        context['staff_present_today'] = HrAttendance.objects.filter(date=today, status='present').count()
        context['staff_on_leave_today'] = LeaveApplication.objects.filter(
            start_date__lte=today, 
            end_date__gte=today, 
            status='approved'
        ).count()

        # --- 2. Chart Data: Staff per Department (Bar Chart) ---
        staff_by_dept = Department.objects.annotate(
            staff_count=Count('staff')
        ).filter(staff_count__gt=0).order_by('-staff_count')

        # To handle 'other' departments correctly, we use the __str__ method's logic
        dept_labels = [str(dept) for dept in staff_by_dept]
        dept_data = [dept.staff_count for dept in staff_by_dept]

        context['department_chart_labels'] = json.dumps(dept_labels)
        context['department_chart_data'] = json.dumps(dept_data)

        # --- 3. Chart Data: Staff by Employment Type (Doughnut Chart) ---
        staff_by_employment = Staff.objects.values('employment_type').annotate(
            count=Count('id')
        ).order_by('employment_type')

        # Get the human-readable display names for the choices
        employment_type_map = dict(Staff.EMPLOYMENT_TYPE_CHOICES)
        employment_labels = [employment_type_map.get(item['employment_type'], 'Unknown') for item in staff_by_employment]
        employment_data = [item['count'] for item in staff_by_employment]

        context['employment_chart_labels'] = json.dumps(employment_labels)
        context['employment_chart_data'] = json.dumps(employment_data)
        
        # --- 4. Recent Activity Tables ---
        # Using select_related to optimize queries by avoiding N+1 problems
        context['recent_hires'] = Staff.objects.select_related(
            'user', 'department', 'designation'
        ).order_by('-joining_date')[:5]

        context['recent_leaves'] = LeaveApplication.objects.select_related(
            'staff__user', 'leave_type'
        ).order_by('-created_at')[:5]

        context['dashboard_title'] = "HR Master Dashboard"
        return context