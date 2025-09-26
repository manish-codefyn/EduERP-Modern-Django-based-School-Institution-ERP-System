from django.contrib import admin
from .models import AcademicYear, Class, Section, House, Subject, Timetable


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('name', 'institution', 'start_date', 'end_date', 'is_current')
    list_filter = ('institution', 'is_current')
    search_fields = ('name',)


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'institution', 'capacity', 'room_number', 'is_active')
    list_filter = ('institution', 'is_active')
    search_fields = ('name', 'code', 'room_number')


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'class_name', 'institution', 'capacity', 'is_active')
    list_filter = ('institution', 'class_name__name', 'is_active')
    search_fields = ('name', 'class_name__name')


@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'institution', 'color', 'is_active')
    list_filter = ('institution', 'is_active')
    search_fields = ('name', 'color')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'code', 'institution', 'subject_type',
        'difficulty_level', 'credits', 'department', 'is_active'
    )
    list_filter = ('institution', 'subject_type', 'difficulty_level', 'department', 'is_active')
    search_fields = ('name', 'code', 'description')


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = (
        'class_name', 'section', 'academic_year', 'day',
        'period', 'subject', 'teacher', 'start_time', 'end_time', 'room', 'is_active'
    )
    list_filter = ('institution', 'academic_year', 'day', 'class_name', 'section', 'is_active')
    search_fields = ('class_name__name', 'section__name', 'subject__name', 'teacher__first_name', 'teacher__last_name')
    ordering = ('day', 'period')
