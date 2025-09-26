# student_portal/views.py
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from core.models import User

class StudentPortalMixin:
    """Mixin to ensure only students can access these views"""
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_student:
            from django.shortcuts import redirect
            return redirect('access_denied')
        return super().dispatch(request, *args, **kwargs)

class StudentDashboardView(StudentPortalMixin, TemplateView):
    """Main student dashboard"""
    template_name = 'student_portal/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Student Portal - Dashboard'
        context['student'] = self.request.user
        
        # Add student-specific data
        context['today_attendance'] = self.get_today_attendance()
        context['upcoming_classes'] = self.get_upcoming_classes()
        context['recent_grades'] = self.get_recent_grades()
        
        return context
    
    def get_today_attendance(self):
        # Mock data - replace with actual implementation
        return {'status': 'present', 'time': '08:30 AM'}
    
    def get_upcoming_classes(self):
        # Mock data
        return [
            {'subject': 'Mathematics', 'time': '10:00 AM', 'teacher': 'Mr. Sharma'},
            {'subject': 'Science', 'time': '11:30 AM', 'teacher': 'Ms. Patel'},
        ]
    
    def get_recent_grades(self):
        # Mock data
        return [
            {'subject': 'Mathematics', 'grade': 'A', 'date': '2024-01-15'},
            {'subject': 'Science', 'grade': 'B+', 'date': '2024-01-10'},
        ]

class StudentTimetableView(StudentPortalMixin, TemplateView):
    """Student class timetable"""
    template_name = 'student_portal/timetable.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'My Timetable'
        context['timetable'] = self.get_weekly_timetable()
        return context
    
    def get_weekly_timetable(self):
        # Mock timetable data
        return {
            'Monday': [
                {'time': '9:00-10:00', 'subject': 'Mathematics', 'room': 'Room 101'},
                {'time': '10:00-11:00', 'subject': 'Science', 'room': 'Lab 201'},
            ],
            'Tuesday': [
                {'time': '9:00-10:00', 'subject': 'English', 'room': 'Room 102'},
            ],
        }

class StudentGradesView(StudentPortalMixin, ListView):
    """Student grades and results"""
    template_name = 'student_portal/grades.html'
    context_object_name = 'grades'
    
    def get_queryset(self):
        # Mock grades data - replace with actual model queries
        return [
            {'subject': 'Mathematics', 'term1': 'A', 'term2': 'A-', 'final': 'A'},
            {'subject': 'Science', 'term1': 'B+', 'term2': 'A', 'final': 'A-'},
            {'subject': 'English', 'term1': 'A', 'term2': 'A', 'final': 'A'},
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'My Grades'
        return context

class StudentAttendanceView(StudentPortalMixin, TemplateView):
    """Student attendance records"""
    template_name = 'student_portal/attendance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'My Attendance'
        context['attendance_stats'] = self.get_attendance_stats()
        context['monthly_attendance'] = self.get_monthly_attendance()
        return context
    
    def get_attendance_stats(self):
        return {
            'total_days': 90,
            'present': 85,
            'absent': 5,
            'percentage': 94.4
        }
    
    def get_monthly_attendance(self):
        return [
            {'month': 'January', 'present': 22, 'absent': 0},
            {'month': 'February', 'present': 20, 'absent': 1},
        ]

class StudentResourcesView(StudentPortalMixin, TemplateView):
    """Learning resources for students"""
    template_name = 'student_portal/resources.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Learning Resources'
        context['resources'] = self.get_learning_resources()
        return context
    
    def get_learning_resources(self):
        return [
            {'title': 'Mathematics Textbook', 'type': 'PDF', 'subject': 'Math'},
            {'title': 'Science Lab Manual', 'type': 'Document', 'subject': 'Science'},
        ]

class StudentProfileView(StudentPortalMixin, TemplateView):
    """Student profile view"""
    template_name = 'student_portal/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'My Profile'
        context['student_data'] = self.get_student_data()
        return context
    
    def get_student_data(self):
        student = self.request.user
        return {
            'full_name': student.get_full_name(),
            'email': student.email,
            'phone': student.phone,
            'grade_level': 'Grade 10',  # Replace with actual data
            'section': 'A',
            'academic_year': '2024-2025',
        }