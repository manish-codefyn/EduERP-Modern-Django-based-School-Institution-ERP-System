from django.contrib import admin
from .models import FeeStructure, FeeInvoice, Payment

# -------------------
# Fee Structure Admin
# -------------------
@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('name', 'institution', 'academic_year', 'class_name', 'amount', 'is_active')
    list_filter = ('institution', 'academic_year', 'class_name', 'is_active')
    search_fields = ('name', 'class_name__name', 'academic_year__name', 'institution__name')
    ordering = ('-created_at',)
    raw_id_fields = ('institution', 'academic_year', 'class_name')


# -------------------
# Fee Invoice Admin
# -------------------
@admin.register(FeeInvoice)
class FeeInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'student', 'institution', 'academic_year', 'issue_date', 'due_date', 'total_amount', 'paid_amount', 'status')
    list_filter = ('institution', 'academic_year', 'status', 'issue_date', 'due_date')
    search_fields = ('invoice_number', 'student__first_name', 'student__last_name', 'student__admission_number')
    ordering = ('-issue_date',)
    raw_id_fields = ('student', 'institution', 'academic_year')


# -------------------
# Payment Admin
# -------------------
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_number', 'student', 'invoice', 'institution', 'amount', 'amount_paid', 'balance', 'status', 'payment_mode', 'payment_date')
    list_filter = ('institution', 'status', 'payment_mode', 'payment_date')
    search_fields = ('payment_number', 'student__first_name', 'student__last_name', 'invoice__invoice_number', 'reference_number')
    ordering = ('-payment_date',)
    raw_id_fields = ('student', 'invoice', 'institution')
    readonly_fields = ('balance', 'is_fully_paid')
