# admin.py
from django.contrib import admin
from .models import (
    Institution, Department, Branch, InstitutionCompliance,
    Affiliation, Accreditation, Partnership
)

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'code', 'type', 'is_active', 'established_date')
    list_filter = ('type', 'is_active')
    search_fields = ('name', 'short_name', 'code', 'city', 'state', 'country')
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'institution', 'department_type', 'head_of_department', 'is_active')
    list_filter = ('department_type', 'is_active')
    search_fields = ('name', 'code', 'head_of_department__staff__user__first_name')
    raw_id_fields = ('institution', 'head_of_department')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'institution', 'is_main_campus', 'is_active')
    list_filter = ('is_main_campus', 'is_active')
    search_fields = ('name', 'code', 'city', 'state')
    raw_id_fields = ('institution', 'branch_manager')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(InstitutionCompliance)
class InstitutionComplianceAdmin(admin.ModelAdmin):
    list_display = ('institution', 'gst_number', 'pan_number', 'udise_code', 'aicte_code', 'ugc_code')
    search_fields = ('institution__name', 'gst_number', 'pan_number')
    raw_id_fields = ('institution',)

@admin.register(Affiliation)
class AffiliationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'institution', 'valid_from', 'valid_to', 'is_active', 'renewal_required')
    list_filter = ('is_active', 'renewal_required')
    search_fields = ('name', 'code', 'institution__name')
    raw_id_fields = ('institution',)

@admin.register(Accreditation)
class AccreditationAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade_or_level', 'awarded_by', 'institution', 'valid_from', 'valid_to', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'grade_or_level', 'awarded_by', 'institution__name')
    raw_id_fields = ('institution',)

@admin.register(Partnership)
class PartnershipAdmin(admin.ModelAdmin):
    list_display = ('partner_name', 'partner_type', 'institution', 'start_date', 'end_date', 'is_active')
    list_filter = ('partner_type', 'is_active', 'renewal_required')
    search_fields = ('partner_name', 'contact_person', 'institution__name')
    raw_id_fields = ('institution',)
