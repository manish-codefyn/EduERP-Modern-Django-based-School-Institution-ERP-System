# admin.py
from django.contrib import admin
from .models import (
    Department, Designation, Staff, Faculty,
    LeaveType, LeaveApplication, LeaveBalance,
    Payroll, HrAttendance
)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'department_type', 'head_of_department', 'is_active')
    list_filter = ('department_type', 'is_active')
    search_fields = ('name', 'code', 'head_of_department__user__first_name', 'head_of_department__user__last_name')

@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category', 'grade', 'is_active')
    list_filter = ('category', 'grade', 'is_active')
    search_fields = ('name', 'code')

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'staff_type', 'department', 'designation', 'is_active')
    list_filter = ('staff_type', 'department', 'designation', 'is_active')
    search_fields = ('user__first_name', 'user__last_name', 'employee_id')
    raw_id_fields = ('user', 'department', 'designation', 'reporting_manager', 'institution')

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('staff', 'qualification', 'degree', 'specialization', 'is_class_teacher')
    list_filter = ('qualification', 'specialization', 'is_class_teacher')
    search_fields = ('staff__user__first_name', 'staff__user__last_name')
    raw_id_fields = ('staff', 'subjects', 'class_teacher_of')

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'max_days', 'carry_forward', 'requires_approval', 'is_active')
    list_filter = ('carry_forward', 'requires_approval', 'is_active')
    search_fields = ('name', 'code')

@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = ('staff', 'leave_type', 'start_date', 'end_date', 'total_days', 'status', 'approved_by')
    list_filter = ('status', 'leave_type')
    search_fields = ('staff__user__first_name', 'staff__user__last_name')
    raw_id_fields = ('staff', 'leave_type', 'approved_by')

@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('staff', 'leave_type', 'year', 'total_allocated', 'total_used', 'carry_forward', 'balance')
    list_filter = ('year',)
    search_fields = ('staff__user__first_name', 'staff__user__last_name')
    raw_id_fields = ('staff', 'leave_type')

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('staff', 'month', 'year', 'net_salary', 'payment_status')
    list_filter = ('month', 'year', 'payment_status')
    search_fields = ('staff__user__first_name', 'staff__user__last_name')
    raw_id_fields = ('staff', 'institution')

@admin.register(HrAttendance)
class HrAttendanceAdmin(admin.ModelAdmin):
    list_display = ('staff', 'date', 'check_in', 'check_out', 'hours_worked', 'status')
    list_filter = ('status',)
    search_fields = ('staff__user__first_name', 'staff__user__last_name')
    raw_id_fields = ('staff', 'institution')
    date_hierarchy = 'date'
