from django.shortcuts import render,redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, View,DeleteView,UpdateView,DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
import json
from django.db import models

from .models import Attendance, StaffAttendance
from apps.students.models import Student
from apps.teachers.models import Teacher
from apps.hr.models import Staff
# views.py
from .forms import AttendanceForm, StaffAttendanceForm
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
import json
from apps.students.models import Student
from apps.academics.models import Class

from django.utils import timezone
from django.contrib import messages
from apps.core.utils import get_user_institution 
# Import export views
from .export import AttendanceExportView,AttendanceExportDetailView,load_students,load_sections
# Re-export for URL patterns
export_student_attendance = AttendanceExportView.as_view()
export_student_attendance_detail = AttendanceExportDetailView.as_view()
load_sections = load_sections
load_students = load_students

    
class RoleBasedAttendanceMixin(LoginRequiredMixin):
    """Mixin for role-based attendance permissions"""
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission based on their role
        if not self.has_permission():
            messages.error(request, "You don't have permission to access this page.")
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
    
    def has_permission(self):
        user = self.request.user
        
        # Superadmins have all permissions
        if user.is_superadmin:
            return True
            
        # Get the required permission from the view
        required_permission = getattr(self, 'required_permission', None)
        if not required_permission:
            return True
            
        # Check role-based permissions
        if required_permission == 'view_attendance':
            return user.role in [
                user.Role.SUPERADMIN,
                user.Role.INSTITUTION_ADMIN,
                user.Role.PRINCIPAL,
                user.Role.TEACHER,
                user.Role.HR,
                user.Role.ACCOUNTANT
            ]
            
        elif required_permission == 'add_attendance':
            return user.role in [
                user.Role.SUPERADMIN,
                user.Role.INSTITUTION_ADMIN,
                user.Role.PRINCIPAL,
                user.Role.TEACHER,
                user.Role.HR
            ]
            
        elif required_permission == 'change_attendance':
            return user.role in [
                user.Role.SUPERADMIN,
                user.Role.INSTITUTION_ADMIN,
                user.Role.PRINCIPAL,
                user.Role.HR
            ]
            
        elif required_permission == 'delete_attendance':
            return user.role in [
                user.Role.SUPERADMIN,
                user.Role.INSTITUTION_ADMIN
            ]
            
        return False
    
    def get_queryset_base(self):
        """Base queryset filtered by user's institution and role"""
        user = self.request.user
        institution = user.profile.institution if hasattr(user, 'profile') and user.profile.institution else None
        
        if not institution:
            return self.model.objects.none()
        
        queryset = self.model.objects.filter(institution=institution)
        
        # Role-based filtering
        if user.is_teacher:
            # Teachers can only see attendance for their classes/students
            if hasattr(self.model, 'student'):
                # For student attendance
                from apps.academics.models import Class  # Avoid circular import
                teacher_classes = Class.objects.filter(teacher__user=user).values_list('class_id', flat=True)
                queryset = queryset.filter(student__current_class_id__in=teacher_classes)
            elif hasattr(self.model, 'staff'):
                # For staff attendance - teachers can only see their own
                queryset = queryset.filter(staff__user=user)
                
        elif user.is_student:
            # Students can only see their own attendance
            queryset = queryset.filter(student__user=user)
            
        elif user.is_parent:
            # Parents can only see their children's attendance
            # Example if Guardian model exists
            children = Student.objects.filter(guardians__user=user).values_list('id', flat=True)

            queryset = queryset.filter(student_id__in=children)
            
        elif user.role == user.Role.HR:
            # HR can see all staff attendance
            if hasattr(self.model, 'staff'):
                queryset = queryset.all()  # HR can see all staff attendance
            else:
                queryset = queryset.none()  # HR can't see student attendance
                
        return queryset

# -------------------------------
# Student Attendance Update/Delete
# -------------------------------

class AttendanceListView(RoleBasedAttendanceMixin,ListView):
    model = Attendance
    template_name = 'attendance/attendance_list.html'
    context_object_name = 'attendance_list'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        institution = get_user_institution(self.request.user)

        if institution:
            queryset = queryset.filter(institution=institution)
        
        # Apply filters from URL parameters
        class_id = self.request.GET.get('class_id')
        date = self.request.GET.get('date')
        status = self.request.GET.get('status')
        
        if class_id:
            queryset = queryset.filter(student__current_class_id=class_id)
        if date:
            queryset = queryset.filter(date=date)
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset.select_related('student__user', 'student__current_class')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()  # filtered data
        institution = get_user_institution(self.request.user)

        # Stats counts
        total_records = queryset.count()
        present_count = queryset.filter(status="present").count()
        absent_count = queryset.filter(status="absent").count()
        leave_count = queryset.filter(status="leave").count()

        # Classes for dropdown
        if institution:
            classes = Class.objects.filter(
                institution=institution,
                is_active=True
            ).annotate(student_count=models.Count('students'))
        else:
            classes = Class.objects.none()
        
        context.update({
            'classes': classes,
            'today': timezone.now().date(),
            'total_records': total_records,
            'present_count': present_count,
            'absent_count': absent_count,
            'leave_count': leave_count,
        })
        return context


class MarkAttendanceView(RoleBasedAttendanceMixin, View):
    template_name = 'attendance/mark_attendance.html'
    required_permission = 'add_attendance'

    def get(self, request):
        # Get class and date from request parameters
        class_id = request.GET.get('class_id')
        date = request.GET.get('date')
        
        if not class_id or not date:
            messages.error(request, 'Please select a class and date')
            return redirect('attendance:attendance_list')
        
        try:
            class_obj = Class.objects.get(id=class_id, institution=request.user.profile.institution)
            
            students = Student.objects.filter(
                current_class=class_obj,
                status="ACTIVE"
            ).select_related('user').order_by('roll_number')  # <-- Order by roll number
            
            context = {
                'students': students,
                'class_name': class_obj.name,
                'class_id': class_id,
                'selected_date': date,
            }
            return render(request, self.template_name, context)
            
        except Class.DoesNotExist:
            messages.error(request, 'Class not found')
            return redirect('attendance:attendance_list')


    def post(self, request):
        try:
            data = json.loads(request.POST.get('attendance_data', '{}'))
            date = request.POST.get('date')
            class_id = request.POST.get('class_id')
            
            if not all([data, date, class_id]):
                messages.error(request, 'Invalid attendance data')
                return redirect('attendance:attendance_list')
            
            with transaction.atomic():
                for student_id, status in data.items():
                    student = Student.objects.get(
                        id=student_id,
                        institution=request.user.profile.institution
                    )
                    
                    Attendance.objects.update_or_create(
                        institution=request.user.profile.institution,
                        student=student,
                        date=date,
                        defaults={
                            'status': status,
                            'marked_by': request.user,
                            'remarks': f'Marked via interactive interface'
                        }
                    )
            
            messages.success(request, f'Attendance marked successfully for {len(data)} students!')
            return redirect('attendance:attendance_list')
            
        except Exception as e:
            messages.error(request, f'Error marking attendance: {str(e)}')
            return redirect('attendance:attendance_list')


class GetClassStudentsView(RoleBasedAttendanceMixin, View):
    """API endpoint to get students for a class (for AJAX)"""
    
    def get(self, request):
        class_id = request.GET.get('class_id')
        if not class_id:
            return JsonResponse({'error': 'Class ID required'}, status=400)
        
        try:
            students = Student.objects.filter(
                current_class_id=class_id,
                institution=request.user.profile.institution,
                is_active=True
            ).select_related('user')
            
            student_data = []
            for student in students:
                student_data.append({
                    'id': student.id,
                    'name': student.user.get_full_name(),
                    'roll_number': student.roll_number,
                    'profile_picture': student.profile_picture.url if student.profile_picture else '',
                    'current_status': None  # You can add current attendance status if needed
                })
            
            return JsonResponse({'students': student_data})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


class AttendanceDetailView(RoleBasedAttendanceMixin, DetailView):
    model = Attendance
    template_name = 'attendance/attendance_detail.html'
    required_permission = 'view_attendance'

    def get_queryset(self):
        return super().get_queryset_base().select_related('student__user', 'institution')



class AttendanceUpdateView(RoleBasedAttendanceMixin, UpdateView):
    model = Attendance
    form_class = AttendanceForm
    template_name = "attendance/attendance_form.html"
    required_permission = "change_attendance"
    success_url = reverse_lazy("attendance:attendance_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Attendance updated for {form.instance.student}.")
        return super().form_valid(form)


class AttendanceDeleteView(RoleBasedAttendanceMixin, DeleteView):
    model = Attendance
    template_name = "attendance/attendance_confirm_delete.html"
    success_url = reverse_lazy("attendance:attendance_list")
    required_permission = "delete_attendance"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superadmin:
            messages.error(request, "Only Superadmin can delete attendance records.")
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
    
    
# -------------------------------
# Staff Attendance Update/Delete
# -------------------------------

class StaffAttendanceUpdateView(RoleBasedAttendanceMixin, UpdateView):
    model = StaffAttendance
    form_class = StaffAttendanceForm
    template_name = "attendance/staff_attendance_form.html"
    required_permission = "change_attendance"
    success_url = reverse_lazy("attendance:staff_attendance_list")

    def form_valid(self, form):
        messages.success(self.request, f"Staff attendance updated for {form.instance.staff}.")
        return super().form_valid(form)


class StaffAttendanceDeleteView(RoleBasedAttendanceMixin, DeleteView):
    model = StaffAttendance
    template_name = "attendance/staff_attendance_confirm_delete.html"
    success_url = reverse_lazy("attendance:staff_attendance_list")
    required_permission = "delete_attendance"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superadmin:
            messages.error(request, "Only Superadmin can delete staff attendance records.")
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class StaffAttendanceListView(RoleBasedAttendanceMixin, ListView):
    model = StaffAttendance
    template_name = 'attendance/staff_attendance_list.html'
    required_permission = 'view_attendance'
    
    def get_queryset(self):
        queryset = super().get_queryset_base()
        date = self.request.GET.get('date')
        
        if date:
            queryset = queryset.filter(date=date)
            
        return queryset.select_related('staff__user', 'institution')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['date'] = self.request.GET.get('date', '')
        return context

    
class StaffAttendanceDetailView(RoleBasedAttendanceMixin, DetailView):
    model = StaffAttendance
    template_name = 'attendance/staff_attendance_detail.html'
    required_permission = 'view_attendance'

    def get_queryset(self):
        return super().get_queryset_base().select_related('staff__user', 'institution')
    
    
class MarkStaffAttendanceView(RoleBasedAttendanceMixin, CreateView):
    model = StaffAttendance
    form_class = StaffAttendanceForm
    template_name = 'attendance/mark_staff_attendance.html'
    required_permission = 'add_attendance'
    success_url = reverse_lazy('staff_attendance_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        
        # Limit staff choices based on user role
        if user.role == user.Role.HR:
            # HR can mark attendance for all staff
            form.fields['staff'].queryset = Staff.objects.filter(
                institution=self.request.user.profile.institution,
                is_active=True
            )
        elif user.is_teacher:
            # Teachers can only mark their own attendance (if allowed)
            form.fields['staff'].queryset = Staff.objects.filter(user=user)
        else:
            form.fields['staff'].queryset = Staff.objects.none()
            
        return form
    
    def form_valid(self, form):
        form.instance.institution = self.request.user.profile.institution
        form.instance.marked_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Attendance marked for {self.object.staff}.')
        return response


@method_decorator(csrf_exempt, name='dispatch')
class BulkAttendanceView(RoleBasedAttendanceMixin, View):
    required_permission = 'add_attendance'
    
    def post(self, request):
        try:
            user = request.user
            institution = user.profile.institution if hasattr(user, 'profile') and user.profile.institution else None
            
            if not institution:
                return JsonResponse({'success': False, 'message': 'No institution assigned'})
                
            data = json.loads(request.body)
            date = data.get('date')
            class_id = data.get('class_id')
            section_id = data.get('section_id')
            attendance_data = data.get('attendance', {})
            
            # Check if user has permission to mark attendance for this class
            if user.is_teacher:
                from apps.academics.models import ClassSubject
                has_access = ClassSubject.objects.filter(
                    teacher__user=user,
                    class_id=class_id
                ).exists()
                if not has_access:
                    return JsonResponse({'success': False, 'message': 'No permission for this class'})
            
            with transaction.atomic():
                students = Student.objects.filter(
                    institution=institution,
                    current_class_id=class_id,
                    section_id=section_id,
                    is_active=True
                )
                
                for student in students:
                    status = attendance_data.get(str(student.id), 'present')
                    Attendance.objects.update_or_create(
                        institution=institution,
                        student=student,
                        date=date,
                        defaults={
                            'status': status,
                            'marked_by': user,
                            'remarks': f'Bulk attendance marked by {user.get_full_name()}'
                        }
                    )
            
            return JsonResponse({'success': True, 'message': 'Attendance marked successfully'})
        
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class BulkStaffAttendanceView(RoleBasedAttendanceMixin, View):
    required_permission = 'add_attendance'
    
    def post(self, request):
        try:
            user = request.user
            institution = user.profile.institution if hasattr(user, 'profile') and user.profile.institution else None
            
            if not institution:
                return JsonResponse({'success': False, 'message': 'No institution assigned'})
                
            data = json.loads(request.body)
            date = data.get('date')
            department_id = data.get('department_id')
            attendance_data = data.get('attendance', {})
            
            # Check if user has permission to mark staff attendance
            if user.role != user.Role.HR and not user.is_superadmin and not user.is_institution_admin:
                return JsonResponse({'success': False, 'message': 'No permission to mark staff attendance'})
            
            with transaction.atomic():
                if department_id:
                    staff_members = Staff.objects.filter(
                        institution=institution,
                        department_id=department_id,
                        is_active=True
                    )
                else:
                    staff_members = Staff.objects.filter(
                        institution=institution,
                        is_active=True
                    )
                
                for staff in staff_members:
                    status = attendance_data.get(str(staff.id), 'present')
                    StaffAttendance.objects.update_or_create(
                        institution=institution,
                        staff=staff,
                        date=date,
                        defaults={
                            'status': status,
                            'marked_by': user,
                            'remarks': f'Bulk staff attendance marked by {user.get_full_name()}'
                        }
                    )
            
            return JsonResponse({'success': True, 'message': 'Staff attendance marked successfully'})
        
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})


class AttendanceReportView(RoleBasedAttendanceMixin, View):
    template_name = 'attendance/attendance_report.html'
    required_permission = 'view_attendance'
    
    def get(self, request):
        user = request.user
        institution = user.profile.institution if hasattr(user, 'profile') and user.profile.institution else None
        
        if not institution:
            messages.error(request, "No institution assigned")
            return render(request, self.template_name)
        
        # Get report parameters
        report_type = request.GET.get('type', 'student')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        class_id = request.GET.get('class_id')
        department_id = request.GET.get('department_id')
        
        context = {
            'report_type': report_type,
            'start_date': start_date,
            'end_date': end_date,
            'class_id': class_id,
            'department_id': department_id,
        }
        
        # Generate report based on user role and permissions
        if report_type == 'student' and user.has_permission('attendance', 'view'):
            queryset = Attendance.objects.filter(
                institution=institution,
                date__range=[start_date, end_date] if start_date and end_date else None
            )
            
            if class_id and user.has_permission('students', 'view'):
                queryset = queryset.filter(student__current_class_id=class_id)
                
            context['attendance_data'] = queryset.select_related('student__user')
            
        elif report_type == 'staff' and user.has_permission('hr', 'view'):
            queryset = StaffAttendance.objects.filter(
                institution=institution,
                date__range=[start_date, end_date] if start_date and end_date else None
            )
            
            if department_id and user.has_permission('hr', 'view'):
                queryset = queryset.filter(staff__department_id=department_id)
                
            context['attendance_data'] = queryset.select_related('staff__user')
        
        return render(request, self.template_name, context)