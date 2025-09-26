# transport/admin.py
from django.contrib import admin
from .models import (
    Vehicle, Driver, Route, RouteStop,
    TransportAssignment, StudentTransport,
    TransportAttendance, MaintenanceRecord
)


class RouteStopInline(admin.TabularInline):
    """Inline stops under a Route"""
    model = RouteStop
    extra = 1
    ordering = ["sequence"]


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "start_point", "end_point", "distance", "fare", "is_active")
    list_filter = ("institution", "is_active")
    search_fields = ("name", "start_point", "end_point")
    ordering = ("name",)
    inlines = [RouteStopInline]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "vehicle_number", "institution", "vehicle_type", "make", "model",
        "year", "capacity", "fuel_type", "is_active"
    )
    list_filter = ("institution", "vehicle_type", "fuel_type", "is_active")
    search_fields = ("vehicle_number", "make", "model")
    ordering = ("vehicle_number",)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("user", "institution", "license_number", "license_type", "experience", "is_active")
    list_filter = ("institution", "license_type", "is_active")
    search_fields = ("user__first_name", "user__last_name", "user__email", "license_number")
    ordering = ("user__first_name",)


@admin.register(TransportAssignment)
class TransportAssignmentAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "driver", "route", "institution", "start_date", "end_date", "is_active")
    list_filter = ("institution", "is_active", "route", "vehicle")
    search_fields = ("vehicle__vehicle_number", "driver__user__first_name", "driver__user__last_name")
    ordering = ("-start_date",)


@admin.register(StudentTransport)
class StudentTransportAdmin(admin.ModelAdmin):
    list_display = ("student", "transport_assignment", "pickup_stop", "drop_stop", "start_date", "is_active")
    list_filter = ("institution", "is_active", "start_date", "transport_assignment__route")
    search_fields = ("student__first_name", "student__last_name", "student__admission_number")
    ordering = ("-start_date",)


@admin.register(TransportAttendance)
class TransportAttendanceAdmin(admin.ModelAdmin):
    list_display = ("student_transport", "date", "pickup_status", "drop_status", "recorded_by")
    list_filter = ("institution", "pickup_status", "drop_status", "date")
    search_fields = (
        "student_transport__student__first_name",
        "student_transport__student__last_name",
        "student_transport__student__admission_number",
    )
    ordering = ("-date",)


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "maintenance_type", "date", "odometer_reading", "cost", "next_due_date")
    list_filter = ("institution", "maintenance_type", "date")
    search_fields = ("vehicle__vehicle_number", "description", "garage")
    ordering = ("-date",)
