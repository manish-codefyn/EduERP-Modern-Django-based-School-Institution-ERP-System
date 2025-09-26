from django.contrib import admin
from .models import (
    Hostel, HostelFacility, Room, RoomAmenity, HostelAllocation,
    HostelFeeStructure, HostelAttendance, HostelVisitorLog,
    HostelInventory, MaintenanceRequest
)

@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    list_display = ('name', 'institution', 'gender_type', 'capacity', 'current_occupancy', 'is_active')
    list_filter = ('institution', 'gender_type', 'is_active')
    search_fields = ('name', 'code', 'warden__first_name', 'assistant_warden__first_name')

@admin.register(HostelFacility)
class HostelFacilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'institution', 'icon')
    list_filter = ('institution',)
    search_fields = ('name', 'description')

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'hostel', 'institution', 'floor', 'room_type', 'capacity', 'current_occupancy', 'is_available')
    list_filter = ('hostel', 'institution', 'floor', 'room_type', 'is_available')
    search_fields = ('room_number',)

@admin.register(RoomAmenity)
class RoomAmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'institution')
    list_filter = ('institution',)
    search_fields = ('name', 'description')

@admin.register(HostelAllocation)
class HostelAllocationAdmin(admin.ModelAdmin):
    list_display = ('student', 'room', 'institution', 'date_from', 'date_to', 'is_active')
    list_filter = ('institution', 'is_active', 'date_from')
    search_fields = ('student__first_name', 'student__last_name', 'room__room_number')

@admin.register(HostelFeeStructure)
class HostelFeeStructureAdmin(admin.ModelAdmin):
    list_display = ('hostel', 'institution', 'room_type', 'amount', 'frequency', 'effective_from', 'is_active')
    list_filter = ('institution', 'hostel', 'room_type', 'frequency', 'is_active')

@admin.register(HostelAttendance)
class HostelAttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'institution', 'date', 'present', 'recorded_by')
    list_filter = ('institution', 'present', 'date')
    search_fields = ('student__first_name', 'student__last_name')

@admin.register(HostelVisitorLog)
class HostelVisitorLogAdmin(admin.ModelAdmin):
    list_display = ('visitor_name', 'student_visited', 'institution', 'purpose', 'entry_time', 'exit_time')
    list_filter = ('institution', 'entry_time')
    search_fields = ('visitor_name', 'student_visited__first_name', 'student_visited__last_name')

@admin.register(HostelInventory)
class HostelInventoryAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'hostel', 'institution', 'quantity', 'condition', 'last_maintenance', 'next_maintenance')
    list_filter = ('institution', 'hostel', 'condition')
    search_fields = ('item_name',)

@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'hostel', 'institution', 'room', 'priority', 'status', 'requested_by', 'assigned_to', 'requested_date')
    list_filter = ('institution', 'priority', 'status', 'requested_date')
    search_fields = ('title', 'description', 'requested_by__first_name', 'assigned_to__first_name')
