# admin.py
from django.contrib import admin
from .models import Attendance, StaffAttendance

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'status', 'marked_by', 'institution')
    list_filter = ('status', 'date', 'institution')
    search_fields = ('student__first_name', 'student__last_name', 'student__admission_number')
    date_hierarchy = 'date'
    ordering = ('-date',)
    raw_id_fields = ('student', 'marked_by', 'institution')

@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ('staff', 'date', 'status', 'marked_by', 'institution')
    list_filter = ('status', 'date', 'institution')
    search_fields = ('staff__user__first_name', 'staff__user__last_name')
    date_hierarchy = 'date'
    ordering = ('-date',)
    raw_id_fields = ('staff', 'marked_by', 'institution')
