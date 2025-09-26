# apps/examination/admin.py

from django.contrib import admin
from .models import ExamType, Exam, ExamSubject, ExamResult


@admin.register(ExamType)
class ExamTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "institution", "is_active")
    list_filter = ("is_active", "institution")
    search_fields = ("name", "code")
    ordering = ("name",)


class ExamSubjectInline(admin.TabularInline):
    model = ExamSubject
    extra = 1


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("name", "exam_type", "institution", "academic_year", "start_date", "end_date", "is_published")
    list_filter = ("exam_type", "institution", "academic_year", "is_published")
    search_fields = ("name",)
    inlines = [ExamSubjectInline]
    ordering = ("-start_date",)


@admin.register(ExamSubject)
class ExamSubjectAdmin(admin.ModelAdmin):
    list_display = ("exam", "subject", "max_marks", "pass_marks", "exam_date", "start_time", "end_time")
    list_filter = ("exam", "subject")
    search_fields = ("exam__name", "subject__name")
    ordering = ("exam_date", "start_time")


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ("student", "exam_subject", "marks_obtained", "grade", "created_at")
    list_filter = ("grade", "exam_subject__exam", "exam_subject__subject")
    search_fields = ("student__first_name", "student__last_name", "exam_subject__exam__name")
    ordering = ("-created_at",)
