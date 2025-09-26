from django.urls import path
from . import views
from . import fee_exports
from . import hostel_exports
from . import hostel_attendance
from . import room_exports
from . import hostel_facility
from . import room_amenity
from . import visitor_log
from . import maintance
from . import inventory

app_name = 'hostel'

urlpatterns = [
    # Hostel URLs
    
    path('inventory/', inventory.HostelInventoryListView.as_view(), name='inventory_list'),
    path('inventory/create/', inventory.HostelInventoryCreateView.as_view(), name='inventory_create'),
    path('inventory/<uuid:pk>/', inventory.HostelInventoryDetailView.as_view(), name='inventory_detail'),
    path('inventory/<uuid:pk>/update/', inventory.HostelInventoryUpdateView.as_view(), name='inventory_update'),
    path('inventory/<uuid:pk>/delete/', inventory.HostelInventoryDeleteView.as_view(), name='inventory_delete'),
    path('inventory/export/',inventory.HostelInventoryExportView.as_view(), name='inventory_export'),
    
    path('maintenance/', maintance.MaintenanceRequestListView.as_view(), name='maintenance_list'),
    path('maintenance/create/', maintance.MaintenanceRequestCreateView.as_view(), name='maintenance_create'),
    path('maintenance/<uuid:pk>/update/', maintance.MaintenanceRequestUpdateView.as_view(), name='maintenance_update'),
    path('maintenance/<uuid:pk>/delete/', maintance.MaintenanceRequestDeleteView.as_view(), name='maintenance_delete'),
    path('maintenance/<uuid:pk>/complete/', maintance.MaintenanceRequestCompleteView.as_view(), name='maintenance_complete'),
    path('maintenance/export/', maintance.MaintenanceRequestExportView.as_view(), name='maintenance_export'),
    path('ajax/load-rooms/', maintance.load_rooms, name='ajax_load_rooms'),
    
    path('visitors/', visitor_log.HostelVisitorLogListView.as_view(), name='visitor_list'),
    path('visitors/add/', visitor_log.HostelVisitorLogCreateView.as_view(), name='visitor_add'),
    path('visitors/<uuid:pk>/edit/',visitor_log.HostelVisitorLogUpdateView.as_view(), name='visitor_edit'),
    path('visitors/<uuid:pk>/delete/', visitor_log.HostelVisitorLogDeleteView.as_view(), name='visitor_delete'),
    path('visitors/<uuid:pk>/exit/', visitor_log.HostelVisitorLogExitView.as_view(), name='visitor_exit'),
    path("visitor-logs/export/", visitor_log.HostelVisitorLogExportView.as_view(), name="visitorlog_export"),
    
    
    path('amenities/', room_amenity.RoomAmenityListView.as_view(), name='amenity_list'),
    path('amenities/add/', room_amenity.RoomAmenityCreateView.as_view(), name='amenity_add'),
    path('amenities/<uuid:pk>/edit/',room_amenity.RoomAmenityUpdateView.as_view(), name='amenity_edit'),
    path('amenities/<uuid:pk>/delete/', room_amenity.RoomAmenityDeleteView.as_view(), name='amenity_delete'),
    
    path('facilities/', hostel_facility.HostelFacilityListView.as_view(), name='facility_list'),
    path('facilities/add/', hostel_facility.HostelFacilityCreateView.as_view(), name='facility_add'),
    path('facilities/<uuid:pk>/edit/', hostel_facility.HostelFacilityUpdateView.as_view(), name='facility_update'),
    path('facilities/<uuid:pk>/delete/',hostel_facility.HostelFacilityDeleteView.as_view(), name='facility_delete'),
    
    
    path('', views.HostelListView.as_view(), name='hostel_list'),
    path('add/', views.HostelCreateView.as_view(), name='hostel_add'),
    path('<uuid:pk>/', views.HostelDetailView.as_view(), name='hostel_detail'),
    path('<uuid:pk>/edit/', views.HostelUpdateView.as_view(), name='hostel_update'),
    path('<uuid:pk>/delete/', views.HostelDeleteView.as_view(), name='hostel_delete'),
    
    # Room URLs
    path('rooms/', views.RoomListView.as_view(), name='room_list'),
    path('rooms/add/', views.RoomCreateView.as_view(), name='room_add'),
    path('rooms/<uuid:pk>/edit/', views.RoomUpdateView.as_view(), name='room_edit'),
    path('rooms/<uuid:pk>/delete/', views.RoomDeleteView.as_view(), name='room_delete'),
    path('export/rooms/', room_exports.RoomExportView.as_view(), name='room_export'),
    
    # Allocation URLs
    path('allocations/', views.HostelAllocationListView.as_view(), name='allocation_list'),
    path('allocations/add/', views.HostelAllocationCreateView.as_view(), name='allocation_add'),
    path('allocations/<uuid:pk>/edit/', views.HostelAllocationUpdateView.as_view(), name='allocation_edit'),
    path('allocations/<uuid:pk>/delete/', views.HostelAllocationDeleteView.as_view(), name='allocation_delete'),
    path('fee-structures/export/', fee_exports.FeeStructureExportView.as_view(), name='feestructure_export'),
    # Fee Structure URLs
    path('fee-structures/', views.HostelFeeStructureListView.as_view(), name='feestructure_list'),
    path('fee-structures/add/', views.HostelFeeStructureCreateView.as_view(), name='feestructure_add'),
    path('fee-structures/<uuid:pk>/', views.HostelFeeStructureDetailView.as_view(), name='feestructure_detail'),
    path('fee-structures/<uuid:pk>/edit/', views.HostelFeeStructureUpdateView.as_view(), name='feestructure_update'),
    path('fee-structures/<uuid:pk>/delete/', views.HostelFeeStructureDeleteView.as_view(), name='feestructure_delete'),
    
    # Export URL
    path('export/', hostel_exports.HostelExportView.as_view(), name='hostel_export'),
    
       # Hostel Attendance URLs
    path('attendance/', hostel_attendance.HostelAttendanceListView.as_view(), name='attendance_list'),
    path('attendance/add/', hostel_attendance.HostelAttendanceCreateView.as_view(), name='attendance_add'),
    path('attendance/<uuid:pk>/', hostel_attendance.HostelAttendanceDetailView.as_view(), name='attendance_detail'),
    path('attendance/<uuid:pk>/edit/', hostel_attendance.HostelAttendanceUpdateView.as_view(), name='attendance_update'),
    path('attendance/<uuid:pk>/delete/', hostel_attendance.HostelAttendanceDeleteView.as_view(), name='attendance_delete'),
    path('attendance/export/', hostel_attendance.HostelAttendanceExportView.as_view(), name='attendance_export'),
    

]