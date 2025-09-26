from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, ListView, DetailView
from django.http import JsonResponse
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from apps.students.models import Student, StudentPortalNotification, StudentPortalSettings, StudentDashboard,StudentHistory
from apps.core.utils import get_user_institution
from apps.core.mixins import StudentPortalMixin
from apps.academics.models import Timetable,AcademicYear
from apps.attendance.models import Attendance


class StudentFunGame(TemplateView):
    template_name = "student_portal/fun_game.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        student = get_object_or_404(Student, user=self.request.user, institution=institution)
        context['page_title'] = 'My Grades'
        context['student'] = student
        context['student_data'] = {
            'full_name': student.full_name,
            'email': student.email,
            'phone': student.mobile or '',
            'grade_level': getattr(student.current_class, 'name', 'N/A'),
            'section': getattr(student.section, 'name', 'N/A'),
            'academic_year': getattr(student.academic_year, 'name', 'N/A'),
        }
        context['student_photo'] = student.get_photo().file.url if student.get_photo() else None
        return context


@method_decorator(login_required, name='dispatch')
class StudentPortalDashboard(TemplateView):
    """Main student portal dashboard integrating all apps"""
    template_name = 'student_portal/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        student = get_object_or_404(Student, user=self.request.user, institution=institution)

        # Update dashboard stats
        dashboard, created = StudentDashboard.objects.get_or_create(
            student=student,
            institution=institution,               
            defaults={"created_by": self.request.user}  
        )
        dashboard.login_count += 1
        dashboard.save()


        # Collect data from different apps
        context.update(self.get_academic_data(student, institution))
        context.update(self.get_attendance_data(student, institution))
        context.update(self.get_exam_data(student, institution))
        context.update(self.get_fee_data(student, institution))
        context.update(self.get_notification_data(student, institution))
        context.update(self.get_communication_data(student))

        context['student'] = student
        context['dashboard'] = dashboard
        context['institution'] = institution

        return context

    def get_academic_data(self, student, institution):
        """Get academic data from academics app"""
        try:
            from academics.models import Subject
            current_class = student.current_class
            subjects = Subject.objects.filter(
                class_name=current_class,
                institution=institution
            ) if current_class else []

            return {
                'current_class': current_class,
                'section': student.section,
                'subjects': subjects,
                'total_subjects': subjects.count(),
            }
        except ImportError:
            return {'academic_data_available': False}

    def get_attendance_data(self, student, institution):
        """Get attendance data from attendance app"""
        try:
            from apps.attendance.models import Attendance
            today = timezone.now().date()
            month_start = today.replace(day=1)

            # Monthly attendance summary
            monthly_attendance = Attendance.objects.filter(
                student=student,
                institution=institution,
                date__gte=month_start,
                date__lte=today
            ).aggregate(
                total_days=Count('id'),
                present_days=Count('id', filter=Q(status='PRESENT')),
                absent_days=Count('id', filter=Q(status='ABSENT'))
            )

            # Today's status
            today_attendance = Attendance.objects.filter(
                student=student,
                institution=institution,
                date=today
            ).first()

            return {
                'monthly_attendance': monthly_attendance,
                'today_attendance': today_attendance,
                'attendance_percentage': self.calculate_attendance_percentage(monthly_attendance),
            }
        except ImportError:
            return {'attendance_data_available': False}

    def calculate_attendance_percentage(self, attendance_data):
        if attendance_data['total_days'] > 0:
            return (attendance_data['present_days'] / attendance_data['total_days']) * 100
        return 0

    def get_exam_data(self, student, institution):
        """Get exam data from examinations app"""
        try:
            from apps.examination.models import Exam, ExamResult
            current_term = getattr(student, 'current_term', None)

            if current_term:
                recent_exams = Exam.objects.filter(
                    term=current_term,
                    class_name=student.current_class,
                    institution=institution
                ).order_by('-date')[:3]

                recent_results = ExamResult.objects.filter(
                    student=student,
                    exam__in=recent_exams,
                    institution=institution
                ).select_related('exam')[:5]

                return {
                    'recent_exams': recent_exams,
                    'recent_results': recent_results,
                    'upcoming_exams': self.get_upcoming_exams(student, institution),
                }
        except ImportError:
            pass
        return {'exam_data_available': False}

    def get_upcoming_exams(self, student, institution):
        """Get upcoming exams"""
        try:
            from apps.examination.models import Exam
            tomorrow = timezone.now().date() + timedelta(days=1)
            next_week = tomorrow + timedelta(days=7)

            return Exam.objects.filter(
                class_name=student.current_class,
                institution=institution,
                date__gte=tomorrow,
                date__lte=next_week
            ).order_by('date')[:3]
        except ImportError:
            return []

    def get_fee_data(self, student, institution):
        """Get fee data from finance app"""
        try:
            from apps.finance.models import FeeInvoice, Payment

            current_academic_year = student.academic_year

            # Get fee summary from invoices
            fee_summary = FeeInvoice.objects.filter(
                institution=institution,
                student=student,
                academic_year=current_academic_year,
            ).aggregate(
                total_due=Sum("total_amount"),
                total_paid=Sum("paid_amount"),
            )

            total_due = fee_summary.get("total_due") or 0
            total_paid = fee_summary.get("total_paid") or 0
            total_pending = total_due - total_paid

            # Get recent payments
            recent_payments = Payment.objects.filter(
                student=student,
                institution=institution,
                invoice__academic_year=current_academic_year, 
            ).order_by("-payment_date")[:3]

            return {
                "fee_summary": {
                    "total_due": total_due,
                    "total_paid": total_paid,
                    "total_pending": total_pending,
                },
                "recent_payments": recent_payments,
                "total_pending": total_pending,
            }

        except ImportError:
            return {"fee_data_available": False}

    def get_notification_data(self, student, institution):
        """Get notifications for dashboard"""
        unread_count = StudentPortalNotification.objects.filter(
            student=student,
            institution=institution,
            is_read=False
        ).count()

        recent_notifications = StudentPortalNotification.objects.filter(
            student=student,
            institution=institution
        ).order_by('-created_at')[:5]

        return {
            'unread_notifications': unread_count,
            'recent_notifications': recent_notifications,
        }

    def get_communication_data(self, student):
        """Get communication data from communications app"""
        try:
            from communications.models import Message
            unread_messages = Message.objects.filter(
                recipient=student.user,
                is_read=False
            ).count()

            return {
                'unread_messages': unread_messages,
            }
        except ImportError:
            return {'communication_data_available': False}



@method_decorator(login_required, name='dispatch')
class AcademicOverview(TemplateView):
    """Academic overview integrating academics and examinations apps"""
    template_name = 'student_portal/academic_overview.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = get_object_or_404(Student, user=self.request.user)
        
        # Get class schedule
        try:
            from academics.models import Timetable
            timetable = Timetable.objects.filter(
                class_name=student.current_class,
                section=student.section
            ).select_related('subject', 'teacher')
            context['timetable'] = timetable
        except ImportError:
            context['timetable_available'] = False
        
        # Get subjects for the class
        try:
            from academics.models import Subject
            subjects = Subject.objects.filter(class_name=student.current_class)
            context['subjects'] = subjects
        except ImportError:
            context['subjects_available'] = False
        
        # Get recent exam results
        try:
            from examination.models import ExamResult
            recent_results = ExamResult.objects.filter(
                student=student
            ).select_related('exam_subject__exam', 'exam_subject__subject')\
             .order_by('-exam_subject__exam__start_date')[:10]
            context['recent_results'] = recent_results
        except ImportError:
            context['results_available'] = False
        
        context['student'] = student
        return context


@method_decorator(login_required, name='dispatch')
class AttendanceView(TemplateView):
    """Attendance overview integrating attendance app"""
    template_name = 'students/portal/attendance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = get_object_or_404(Student, user=self.request.user)
        
        year = int(self.request.GET.get('year', timezone.now().year))
        month = int(self.request.GET.get('month', timezone.now().month))
        
        try:
            from apps.attendance.models import Attendance
            from django.db.models import Count, Q
            
            # Monthly breakdown
            monthly_data = []
            for m in range(1, 13):
                month_start = datetime(year, m, 1).date()
                if m == 12:
                    month_end = datetime(year, m, 31).date()
                else:
                    month_end = datetime(year, m+1, 1).date() - timedelta(days=1)
                
                attendance_data = Attendance.objects.filter(
                    student=student,
                    date__gte=month_start,
                    date__lte=month_end
                ).aggregate(
                    total=Count('id'),
                    present=Count('id', filter=Q(status='PRESENT')),
                    absent=Count('id', filter=Q(status='ABSENT')),
                    late=Count('id', filter=Q(status='LATE'))
                )
                
                if attendance_data['total'] > 0:
                    percentage = (attendance_data['present'] / attendance_data['total']) * 100
                else:
                    percentage = 0
                
                monthly_data.append({
                    'month': m,
                    'year': year,
                    'data': attendance_data,
                    'percentage': percentage
                })
            
            # Detailed view for selected month
            selected_month_start = datetime(year, month, 1).date()
            if month == 12:
                selected_month_end = datetime(year, month, 31).date()
            else:
                selected_month_end = datetime(year, month+1, 1).date() - timedelta(days=1)
            
            daily_attendance = Attendance.objects.filter(
                student=student,
                date__gte=selected_month_start,
                date__lte=selected_month_end
            ).order_by('date')
            
            context['monthly_data'] = monthly_data
            context['daily_attendance'] = daily_attendance
            context['selected_year'] = year
            context['selected_month'] = month
            context['attendance_available'] = True
            
        except ImportError:
            context['attendance_available'] = False
        
        context['student'] = student
        return context


@method_decorator(login_required, name='dispatch')
class FeeView(TemplateView):
    """Fee overview integrating finance app"""
    template_name = 'students/portal/fees.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = get_object_or_404(Student, user=self.request.user)
        
        try:
            from apps.finance.models import FeeStructure, Payment, FeeInvoice
            
            # Current fee status
            current_fees = FeeStructure.objects.filter(
                student=student,
                academic_year=student.academic_year,
                is_active=True
            ).select_related('fee_type')
            
            # Payment history
            payment_history = Payment.objects.filter(
                fee__student=student
            ).select_related('fee', 'fee__fee_type').order_by('-payment_date')[:20]
            
            # Upcoming installments
            upcoming_installments = FeeInvoice.objects.filter(
                fee__student=student,
                due_date__gte=timezone.now().date(),
                is_paid=False
            ).select_related('fee', 'fee__fee_type').order_by('due_date')[:5]
            
            # Summary
            fee_summary = current_fees.aggregate(
                total_amount=Sum('total_amount'),
                total_paid=Sum('amount_paid'),
                total_due=Sum('amount_due')
            )
            
            context.update({
                'current_fees': current_fees,
                'payment_history': payment_history,
                'upcoming_installments': upcoming_installments,
                'fee_summary': fee_summary,
                'finance_available': True,
            })
            
        except ImportError:
            context['finance_available'] = False
        
        context['student'] = student
        return context


@method_decorator(login_required, name='dispatch')
class NotificationListView(ListView):
    """Student notifications list"""
    model = StudentPortalNotification
    template_name = 'student_portal/notifications.html'
    paginate_by = 20
    context_object_name = 'notifications'
    
    def get_queryset(self):
        student = get_object_or_404(Student, user=self.request.user)
        return StudentPortalNotification.objects.filter(student=student).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = get_object_or_404(Student, user=self.request.user)
        context['student'] = student


@method_decorator(login_required, name='dispatch')
class LibraryView(TemplateView):
    """Library overview integrating library app"""
    template_name = 'student_portal/library.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = get_object_or_404(Student, user=self.request.user)
        
        try:
            from apps.library.models import BorrowRecord, Book
            
            # Currently issued books
            issued_books = BorrowRecord.objects.filter(
                borrower=student.user,
                returned_date__isnull=True
            ).select_related('book')
            
            # Reading history (last 10 borrowings)
            reading_history = BorrowRecord.objects.filter(
                borrower=student.user
            ).select_related('book').order_by('-borrowed_date')[:10]
            
            # Overdue books
            overdue_books = BorrowRecord.objects.filter(
                borrower=student.user,
                returned_date__isnull=True,
                due_date__lt=timezone.now()
            ).select_related('book')
            
            context.update({
                'issued_books': issued_books,
                'reading_history': reading_history,
                'overdue_books': overdue_books,
                'library_available': True,
            })
            
        except ImportError:
            context['library_available'] = False
        
        context['student'] = student
        return context



@method_decorator(login_required, name='dispatch')
class HostelView(TemplateView):
    """Hostel overview integrating hostel app"""
    template_name = 'students/portal/hostel.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = get_object_or_404(Student, user=self.request.user)
        
        try:
            from apps.hostel.models import HostelAllocation, HostelFeeStructure
            
            # Hostel allocation
            allocation = HostelAllocation.objects.filter(
                student=student,
                is_active=True
            ).select_related('hostel', 'room').first()
            
            # Hostel fees
            hostel_fees = HostelFeeStructure.objects.filter(
                student=student,
                academic_year=student.academic_year
            ).order_by('-due_date')
            
            context.update({
                'allocation': allocation,
                'hostel_fees': hostel_fees,
                'hostel_available': True,
            })
            
        except ImportError:
            context['hostel_available'] = False
        
        context['student'] = student
        return context

class StudentTimetableView(TemplateView):
    template_name = "student_portal/timetable.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user.student_profile  # OneToOne from User to Student

        today = timezone.now().date()
        weekday = today.strftime("%A").lower()  # e.g., 'monday'

        # Get current academic year for the student
        academic_year = student.academic_year

        # Fetch today’s classes for this student
        todays_classes = Timetable.objects.filter(
            institution=student.institution,
            academic_year=academic_year,
            class_name=student.current_class,
            section=student.section,
            day=weekday,
            is_active=True
        ).order_by('period')

        # Attendance percentage calculation for the academic year
        total_days = Attendance.objects.filter(
            student=student,
            date__range=[academic_year.start_date, academic_year.end_date]
        ).count()

        present_days = Attendance.objects.filter(
            student=student,
            date__range=[academic_year.start_date, academic_year.end_date],
            status='present'
        ).count()

        attendance_percentage = 0
        if total_days > 0:
            attendance_percentage = round((present_days / total_days) * 100, 2)

        context.update({
            "student": student,
            "todays_classes": todays_classes,
            "attendance_percentage": attendance_percentage,
            "today": today,
        })
        return context

class StudentGradesView(StudentPortalMixin, ListView):
    """Student grades and results"""
    template_name = 'student_portal/grades.html'
    context_object_name = 'grades'
    
    def get_queryset(self):
        # Get the logged-in student's profile
        self.student = get_object_or_404(Student, user=self.request.user)
        
        # Return StudentHistory for this student for all academic years
        return StudentHistory.objects.filter(student=self.student).order_by('-academic_year__start_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'My Grades'
        context['student'] = self.student
        context['student_data'] = {
            'full_name': self.student.full_name,
            'email': self.student.email,
            'phone': self.student.mobile or '',
            'grade_level': getattr(self.student.current_class, 'name', 'N/A'),
            'section': getattr(self.student.section, 'name', 'N/A'),
            'academic_year': getattr(self.student.academic_year, 'name', 'N/A'),
        }
        context['student_photo'] = self.student.get_photo().file.url if self.student.get_photo() else None
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
        
        # Get the student object from the Student model based on the logged-in user
        student = get_object_or_404(Student, user=self.request.user)
        
        context['page_title'] = 'My Profile'
        context['student_data'] = {
            'full_name': student.full_name,  # using @property full_name
            'email': student.email,
            'phone': student.mobile or '',
            'grade_level': getattr(student.current_class, 'name', 'N/A'),
            'section': getattr(student.section, 'name', 'N/A'),
            'academic_year': getattr(student.academic_year, 'name', 'N/A'),
        }
        context['student'] = student
        context['student_photo'] = student.get_photo().file.url if student.get_photo() else None
        
        return context

    
# AJAX Views
@login_required
def mark_notification_read(request, pk):
    """Mark notification as read"""
    if request.method == 'POST':
        notification = get_object_or_404(
            StudentPortalNotification, 
            pk=pk, 
            student__user=request.user
        )
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    if request.method == 'POST':
        student = get_object_or_404(Student, user=request.user)
        StudentPortalNotification.objects.filter(
            student=student, 
            is_read=False
        ).update(is_read=True)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required
def update_portal_settings(request):
    """Update portal settings"""
    if request.method == 'POST':
        student = get_object_or_404(Student, user=request.user)
        
        settings, created = StudentPortalSettings.objects.get_or_create(
            student=student
        )
        settings.theme = request.POST.get('theme', settings.theme)
        settings.language = request.POST.get('language', settings.language)
        settings.notifications_enabled = request.POST.get('notifications_enabled') == 'true'
        settings.save()
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})



