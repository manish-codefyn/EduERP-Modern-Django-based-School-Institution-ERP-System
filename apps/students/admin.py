# students/admin.py
from django.contrib import admin
from .models import (
    Student, Guardian, StudentMedicalInfo, StudentAddress,
    StudentDocument, StudentTransport, StudentHostel,
    StudentHistory, StudentIdentification,
 StudentPortalSettings, StudentDashboard, StudentPortalNotification
)
from django.utils.translation import gettext_lazy as _



@admin.register(StudentPortalSettings)
class StudentPortalSettingsAdmin(admin.ModelAdmin):
    list_display = ("student", "institution", "theme", "language", "notifications_enabled", "created_by", "created_at")
    list_filter = ("institution", "theme", "language", "notifications_enabled", "created_at")
    search_fields = ("student__first_name", "student__last_name", "student__student_id", "institution__name")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("student", "institution", "created_by")


@admin.register(StudentDashboard)
class StudentDashboardAdmin(admin.ModelAdmin):
    list_display = ("student", "institution", "last_login", "login_count", "created_by", "created_at")
    list_filter = ("institution", "created_at")
    search_fields = ("student__first_name", "student__last_name", "student__student_id", "institution__name")
    readonly_fields = ("last_login", "created_at")
    autocomplete_fields = ("student", "institution", "created_by")


@admin.register(StudentPortalNotification)
class StudentPortalNotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "student", "institution", "notification_type", "is_read", "created_by", "created_at")
    list_filter = ("institution", "notification_type", "is_read", "created_at")
    search_fields = ("title", "message", "student__first_name", "student__last_name", "institution__name")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("student", "institution", "created_by")


# ---------------- Inline Admins ----------------
class GuardianInline(admin.TabularInline):
    model = Guardian
    extra = 1


class StudentAddressInline(admin.TabularInline):
    model = StudentAddress
    extra = 1


class StudentDocumentInline(admin.TabularInline):
    model = StudentDocument
    extra = 1


class StudentHistoryInline(admin.TabularInline):
    model = StudentHistory
    extra = 1


# ---------------- Main Admin ----------------
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("admission_number", "full_name", "institution", "current_class", "section", "status", "enrollment_date")
    list_filter = ("institution", "status", "gender", "category", "academic_year", "current_class")
    search_fields = ("admission_number", "roll_number", "first_name", "last_name", "email", "mobile")
    ordering = ("admission_number",)
    readonly_fields = ("created_at", "updated_at", "age", "fee_status")
    
    fieldsets = (
        (_("Basic Info"), {
            "fields": (
                "institution", "user", "admission_number", "roll_number",
                "first_name", "last_name", "email", "mobile", "gender", "date_of_birth",
                "status", "admission_type", "enrollment_date"
            )
        }),
        (_("Other Details"), {
            "fields": ("category", "religion", "blood_group", "academic_year", "current_class", "section")
        }),
        (_("System Info"), {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at", "age", "fee_status")
        }),
    )
    
    inlines = [GuardianInline, StudentAddressInline, StudentDocumentInline, StudentHistoryInline]


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ("name", "relation", "student", "phone", "email", "is_primary")
    list_filter = ("relation", "occupation", "is_primary")
    search_fields = ("name", "phone", "email", "student__admission_number")


@admin.register(StudentMedicalInfo)
class StudentMedicalInfoAdmin(admin.ModelAdmin):
    list_display = ("student", "conditions", "allergies", "disability", "emergency_contact_name", "emergency_contact_phone")
    list_filter = ("disability",)
    search_fields = ("student__admission_number", "student__first_name", "student__last_name")


@admin.register(StudentAddress)
class StudentAddressAdmin(admin.ModelAdmin):
    list_display = ("student", "address_type", "city", "state", "pincode", "is_current")
    list_filter = ("address_type", "is_current")
    search_fields = ("city", "state", "pincode", "student__admission_number")


@admin.register(StudentDocument)
class StudentDocumentAdmin(admin.ModelAdmin):
    list_display = ("student", "doc_type", "file", "is_verified", "uploaded_at")
    list_filter = ("doc_type", "is_verified")
    search_fields = ("student__admission_number", "student__first_name", "student__last_name")


@admin.register(StudentTransport)
class StudentTransportAdmin(admin.ModelAdmin):
    list_display = ("student", "route", "pickup_point", "drop_point", "transport_fee", "is_active")
    list_filter = ("is_active", "route")
    search_fields = ("student__admission_number", "pickup_point", "drop_point")


@admin.register(StudentHostel)
class StudentHostelAdmin(admin.ModelAdmin):
    list_display = ("student", "hostel", "room_number", "check_in_date", "check_out_date", "hostel_fee")
    list_filter = ("hostel",)
    search_fields = ("student__admission_number", "room_number")


@admin.register(StudentHistory)
class StudentHistoryAdmin(admin.ModelAdmin):
    list_display = ("student", "academic_year", "class_name", "section", "roll_number", "percentage", "result", "promoted")
    list_filter = ("academic_year", "class_name", "result", "promoted")
    search_fields = ("student__admission_number", "roll_number")


@admin.register(StudentIdentification)
class StudentIdentificationAdmin(admin.ModelAdmin):
    list_display = ("student", "aadhaar_number", "abc_id", "shiksha_id", "pan_number", "passport_number")
    search_fields = ("student__admission_number", "aadhaar_number", "pan_number", "passport_number")
