# attendance/urls.py
from django.urls import path
from . import views
from . import export

app_name = "attendance"

# attendance/urls.py

urlpatterns = [
    # Student attendance
    path("", views.AttendanceListView.as_view(), name="attendance_list"),
    path("mark/", views.MarkAttendanceView.as_view(), name="mark_attendance"),
    path("bulk/", views.BulkAttendanceView.as_view(), name="bulk_attendance"),
    path("<uuid:pk>/", views.AttendanceDetailView.as_view(), name="attendance_detail"),
    path("<uuid:pk>/edit/", views.AttendanceUpdateView.as_view(), name="attendance_update"),
    path("<uuid:pk>/delete/", views.AttendanceDeleteView.as_view(), name="attendance_delete"),

    # Staff attendance
    path("staff/", views.StaffAttendanceListView.as_view(), name="staff_attendance_list"),
    path("staff/mark/", views.MarkStaffAttendanceView.as_view(), name="mark_staff_attendance"),
    path("staff/bulk/", views.BulkStaffAttendanceView.as_view(), name="bulk_staff_attendance"),
    path("staff/<uuid:pk>/", views.StaffAttendanceDetailView.as_view(), name="staff_attendance_detail"),
    path("staff/<uuid:pk>/edit/", views.StaffAttendanceUpdateView.as_view(), name="staff_attendance_update"),
    path("staff/<uuid:pk>/delete/", views.StaffAttendanceDeleteView.as_view(), name="staff_attendance_delete"),

    # Reports
    path('export/',views.export_student_attendance, name='export_attendance'),
    path("export/detail/<uuid:pk>/", views.export_student_attendance_detail, name="attendance_export_detail"),
    path('ajax/load-sections/', views.load_sections, name='ajax_load_sections'),
    path('ajax/load-students/', views.load_students, name='ajax_load_students'),
    path("report/", views.AttendanceReportView.as_view(), name="attendance_report"),
]
