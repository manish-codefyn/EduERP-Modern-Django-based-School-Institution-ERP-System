from django.contrib import admin
from .models import Teacher, TeacherAttendance, TeacherSalary

# Inline for TeacherSalary in Teacher Admin
class TeacherSalaryInline(admin.TabularInline):
    model = TeacherSalary
    extra = 0
    readonly_fields = ('net_salary',)
    fields = ('month', 'basic_salary', 'allowances', 'deductions', 'net_salary', 'payment_date', 'payment_status')
    ordering = ('-month',)

# Inline for TeacherAttendance in Teacher Admin
class TeacherAttendanceInline(admin.TabularInline):
    model = TeacherAttendance
    extra = 0
    fields = ('date', 'status', 'remarks')
    ordering = ('-date',)

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'get_full_name', 'email', 'department', 'designation', 'faculty_type', 'is_class_teacher', 'is_active')
    list_filter = ('department', 'designation', 'faculty_type', 'organization_type', 'is_class_teacher', 'is_active')
    search_fields = ('first_name', 'middle_name', 'last_name', 'email', 'employee_id', 'qualification', 'specialization')
    ordering = ('last_name', 'first_name')
    inlines = [TeacherSalaryInline, TeacherAttendanceInline]
    readonly_fields = ('employee_id',)
    fieldsets = (
        ("Personal Information", {
            'fields': ('first_name', 'middle_name', 'last_name', 'email', 'mobile', 'dob', 'gender', 'blood_group', 'address', 'emergency_contact', 'emergency_contact_name', 'photo')
        }),
        ("Professional Information", {
            'fields': ('qualification', 'specialization', 'joining_date', 'experience', 'salary', 'is_class_teacher', 'teaching_grade_levels', 'organization_type', 'department', 'designation', 'faculty_type', 'subjects', 'class_teacher_of', 'department_head', 'resume', 'degree_certificates')
        }),
        ("System Info", {
            'fields': ('user', 'institution', 'is_active')
        }),
    )
    filter_horizontal = ('subjects',)

@admin.register(TeacherAttendance)
class TeacherAttendanceAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'date', 'status', 'remarks')
    list_filter = ('status', 'date')
    search_fields = ('teacher__first_name', 'teacher__last_name', 'remarks')
    ordering = ('-date',)

@admin.register(TeacherSalary)
class TeacherSalaryAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'month', 'basic_salary', 'allowances', 'deductions', 'net_salary', 'payment_date', 'payment_status')
    list_filter = ('payment_status', 'month')
    search_fields = ('teacher__first_name', 'teacher__last_name')
    ordering = ('-month',)
