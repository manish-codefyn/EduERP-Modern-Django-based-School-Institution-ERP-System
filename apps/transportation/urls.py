from django.urls import path
from . import views
from . import  transport_attendance
from . import  student_transport
from . import  transport_assign
from . import  route_stop
from . import  route
from . import  driver

app_name = 'transport'

urlpatterns = [
    # Vehicles

    path('drivers/', driver.DriverListView.as_view(), name='driver_list'),
    path('drivers/create/', driver.DriverCreateView.as_view(), name='driver_create'),
    path('drivers/<uuid:pk>/update/', driver.DriverUpdateView.as_view(), name='driver_update'),
    path('drivers/<uuid:pk>/delete/', driver.DriverDeleteView.as_view(), name='driver_delete'),
    path('drivers/<uuid:pk>/', driver.DriverDetailView.as_view(), name='driver_detail'),

    # Driver export
    path('drivers/export/', driver.DriverExportView.as_view(), name='driver_export'),

    path('vehicles/', views.VehicleListView.as_view(), name='vehicle_list'),
    path('vehicles/create/', views.VehicleCreateView.as_view(), name='vehicle_create'),
    path('vehicles/<uuid:pk>/', views.VehicleDetailView.as_view(), name='vehicle_detail'),
    path('vehicles/<uuid:pk>/update/', views.VehicleUpdateView.as_view(), name='vehicle_update'),
    path('vehicles/<uuid:pk>/delete/', views.VehicleDeleteView.as_view(), name='vehicle_delete'),
    path('vehicles/export/', views.VehicleExportView.as_view(), name='vehicle_export'),
    
    path('vehicles/<uuid:pk>/maintenance/', views.VehicleMaintenanceCreateView.as_view(), name='maintenance_create'),
    path('vehicles/<uuid:vehicle_pk>/maintenance/<int:maintenance_pk>/delete/', views.VehicleMaintenanceDeleteView.as_view(), name='maintenance_delete'),
    path('vehicles/<uuid:pk>/toggle-status/', views.VehicleToggleStatusView.as_view(), name='vehicle_toggle_status'),
    path('dashboard/', views.TransportDashboardView.as_view(), name='transport-dashboard'),
    

    path('attendance/', transport_attendance.TransportAttendanceListView.as_view(), name='attendance_list'),
    path('attendance/create/', transport_attendance.TransportAttendanceCreateView.as_view(), name='attendance_create'),
    path('attendance/<uuid:pk>/update/', transport_attendance.TransportAttendanceUpdateView.as_view(), name='attendance_update'),
    path('attendance/<uuid:pk>/delete/', transport_attendance.TransportAttendanceDeleteView.as_view(), name='attendance_delete'),
    

    path('student-transports/', student_transport.StudentTransportListView.as_view(), name='student_transport_list'),
    path('student-transports/add/', student_transport.StudentTransportCreateView.as_view(), name='student_transport_create'),
    path('student-transports/<uuid:pk>/edit/', student_transport.StudentTransportUpdateView.as_view(), name='student_transport_update'),
    path('student-transports/<uuid:pk>/delete/', student_transport.StudentTransportDeleteView.as_view(), name='student_transport_delete'),
    path("student-transport/export/", student_transport.StudentTransportExportView.as_view(), name="student_transport_export"),
    
    path('assignments/',transport_assign.TransportAssignmentListView.as_view(), name='assignment_list'),
    path('assignments/create/',transport_assign.TransportAssignmentCreateView.as_view(), name='assignment_create'),
    path('assignments/<uuid:pk>/',transport_assign.TransportAssignmentDetailView.as_view(), name='assignment_detail'),
    path('assignments/<uuid:pk>/update/',transport_assign.TransportAssignmentUpdateView.as_view(), name='assignment_update'),
    path('assignments/<uuid:pk>/delete/',transport_assign.TransportAssignmentDeleteView.as_view(), name='assignment_delete'),
    path('assignments/export/',transport_assign.TransportAssignmentExportView.as_view(), name='assignment_export'),
    path('assignments/<uuid:pk>/toggle-status/', transport_assign.TransportAssignmentToggleStatusView.as_view(), name='assignment_toggle_status'),
# path('vehicles/<uuid:pk>/', views.VehicleDetailView.as_view(), name='vehicle_detail'),
# path('drivers/<uuid:pk>/', views.DriverDetailView.as_view(), name='driver_detail'),
# path('routes/<uuid:pk>/', views.RouteDetailView.as_view(), name='route_detail'),
    # Route URLs
    path('routes/', route.RouteListView.as_view(), name='route_list'),
    path('routes/create/', route.RouteCreateView.as_view(), name='route_create'),
    path('routes/<uuid:pk>/', route.RouteDetailView.as_view(), name='route_detail'),
    path('routes/<uuid:pk>/update/', route.RouteUpdateView.as_view(), name='route_update'),
    path('routes/<uuid:pk>/delete/', route.RouteDeleteView.as_view(), name='route_delete'),
    path('routes/export/', route.RouteExportView.as_view(), name='route_export'),

    path('route-stops/',  route_stop.RouteStopListView.as_view(), name='route_stop_list'),
    path('route-stops/add/',  route_stop.RouteStopCreateView.as_view(), name='route_stop_create'),
    path('route-stops/<uuid:pk>/edit/',  route_stop.RouteStopUpdateView.as_view(), name='route_stop_update'),
    path('route-stops/<uuid:pk>/delete/',  route_stop.RouteStopDeleteView.as_view(), name='route_stop_delete'),
    
    
    
    ]