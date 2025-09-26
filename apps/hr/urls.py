from django.urls import path
from . import views
from . import department
from . import designation
from . import staff
from . import faculty
from . import leave_type
from . import leave_application
from . import leave_balance
from . import payroll
from . import attendance

app_name = "hr"

urlpatterns = [

   # Attendance URLs
    path('attendance/', attendance.AttendanceListView.as_view(), name='attendance_list'),
    path('attendance/create/', attendance.AttendanceCreateView.as_view(), name='attendance_create'),
    path('attendance/<uuid:pk>/',attendance.AttendanceDetailView.as_view(), name='attendance_detail'),
    path('attendance/<uuid:pk>/update/',attendance.AttendanceUpdateView.as_view(), name='attendance_update'),
    path('attendance/<uuid:pk>/delete/', attendance.AttendanceDeleteView.as_view(), name='attendance_delete'),
    
    # Export URLs
    path('attendance/export/', attendance.AttendanceExportView.as_view(), name='attendance_export'),
    path('attendance/<uuid:pk>/export/',attendance.AttendanceDetailExportView.as_view(), name='attendance_detail_export'),

 # Payroll URLs
    path('payroll/', payroll.PayrollListView.as_view(), name='payroll_list'),
    path('payroll/create/', payroll.PayrollCreateView.as_view(), name='payroll_create'),
    path('payroll/<uuid:pk>/', payroll.PayrollDetailView.as_view(), name='payroll_detail'),
    path('payroll/<uuid:pk>/update/', payroll.PayrollUpdateView.as_view(), name='payroll_update'),
    path('payroll/<uuid:pk>/delete/', payroll.PayrollDeleteView.as_view(), name='payroll_delete'),
    path('payroll/export/',payroll.PayrollExportView.as_view(), name='payroll_export'),
    path('payroll/<uuid:pk>/export/', payroll.PayrollDetailExportView.as_view(), name='payroll_detail_export'),


  # Leave Balance URLs
    path('leave-balance/', leave_balance.LeaveBalanceListView.as_view(), name='leave_balance_list'),
    path('leave-balance/create/', leave_balance.LeaveBalanceCreateView.as_view(), name='leave_balance_create'),
    path('leave-balance/<uuid:pk>/', leave_balance.LeaveBalanceDetailView.as_view(), name='leave_balance_detail'),
    path('leave-balance/<uuid:pk>/update/', leave_balance.LeaveBalanceUpdateView.as_view(), name='leave_balance_update'),
    path('leave-balance/<uuid:pk>/delete/',leave_balance.LeaveBalanceDeleteView.as_view(), name='leave_balance_delete'),
    path('leave-balance/export/', leave_balance.LeaveBalanceExportView.as_view(), name='leave_balance_export'),
    path('leave-balance/<uuid:pk>/export/', leave_balance.LeaveBalanceDetailExportView.as_view(), name='leave_balance_detail_export'),
    # Leave Application CRUD
    path('leave-applications/', leave_application.LeaveApplicationListView.as_view(), name='leave_application_list'),
    path('leave-applications/add/',  leave_application.LeaveApplicationCreateView.as_view(), name='leave_application_create'),
    path('leave-applications/<uuid:pk>/',  leave_application.LeaveApplicationDetailView.as_view(),   name='leave_application_detail'),
    path('leave-applications/<uuid:pk>/edit/', leave_application.LeaveApplicationUpdateView.as_view(),  name='leave_application_update'),
    path('leave-applications/<uuid:pk>/delete/',   leave_application.LeaveApplicationDeleteView.as_view(),  name='leave_application_delete'),
    path('leave-applications/<uuid:pk>/review/',  leave_application.LeaveApplicationReviewView.as_view(),   name='leave_application_review'),
    path('leave-applications/export/', leave_application.LeaveApplicationExportView.as_view(), name='leave_application_export'),
    path('leave-applications/<uuid:pk>/export/', leave_application.LeaveApplicationDetailExportView.as_view(), name='leave_application_detail_export'),
    # AJAX endpoint for leave balance
    path('ajax/get-leave-balance/',  leave_application.get_leave_balance,  name='get_leave_balance'),

    path('leave-types/', leave_type.LeaveTypeListView.as_view(), name='leave_type_list'),
    path('leave-types/create/', leave_type.LeaveTypeCreateView.as_view(), name='leave_type_create'),
    path('leave-types/<uuid:pk>/', leave_type.LeaveTypeDetailView.as_view(), name='leave_type_detail'),
    path('leave-types/<uuid:pk>/update/', leave_type.LeaveTypeUpdateView.as_view(), name='leave_type_update'),
    path('leave-types/<uuid:pk>/delete/', leave_type.LeaveTypeDeleteView.as_view(), name='leave_type_delete'),

    path('faculty/', faculty.FacultyListView.as_view(), name='faculty_list'),
    path('faculty/create/', faculty.FacultyCreateView.as_view(), name='faculty_create'),
    path('faculty/<uuid:pk>/', faculty.FacultyDetailView.as_view(), name='faculty_detail'),
    path('faculty/<uuid:pk>/update/', faculty.FacultyUpdateView.as_view(), name='faculty_update'),
    path('faculty/<uuid:pk>/delete/', faculty.FacultyDeleteView.as_view(), name='faculty_delete'),
    path('faculty/export/', faculty.FacultyExportView.as_view(), name='faculty_export'),
    path('faculty/<uuid:pk>/export/', faculty.FacultyDetailExportView.as_view(), name='faculty_detail_export'),
    path('faculty/<uuid:faculty_id>/idcard/', faculty.generate_faculty_id_card, name='faculty_idcard'),

    path('staff/', staff.StaffListView.as_view(), name='staff_list'),
    path('staff/create/', staff.StaffCreateView.as_view(), name='staff_create'),
    path('staff/<uuid:pk>/', staff.StaffDetailView.as_view(), name='staff_detail'),
    path('staff/<uuid:pk>/update/', staff.StaffUpdateView.as_view(), name='staff_update'),
    path('staff/<uuid:pk>/delete/', staff.StaffDeleteView.as_view(), name='staff_delete'),
    path('staff/export/', staff.StaffExportView.as_view(), name='staff_export'),
    path('staff/<uuid:staff_id>/idcard/', staff.generate_staff_id_card, name='staff_idcard'),
    path('staff/<uuid:pk>/export/', staff.StaffDetailExportView.as_view(), name='staff-detail-export'),
    
    path('designation/', designation.DesignationListView.as_view(), name='designation_list'),
    path('designation/create/', designation.DesignationCreateView.as_view(), name='designation_create'),
    path('designation/<uuid:pk>/', designation.DesignationDetailView.as_view(), name='designation_detail'),
    path('designation/<uuid:pk>/update/', designation.DesignationUpdateView.as_view(), name='designation_update'),
    path('designation/<uuid:pk>/delete/',designation.DesignationDeleteView.as_view(), name='designation_delete'),
    path('designation/export/',designation.DesignationExportView.as_view(), name='designation_export'),
    
    path('departments/', department.DepartmentListView.as_view(), name='department_list'),
    path('departments/create/', department.DepartmentCreateView.as_view(), name='department_create'),
    path('departments/<uuid:pk>/update/', department.DepartmentUpdateView.as_view(), name='department_update'),
    path('departments/<uuid:pk>/delete/', department.DepartmentDeleteView.as_view(), name='department_delete'),
    path('departments/<uuid:pk>/detail/', department.DepartmentDetailView.as_view(), name='department_detail'),
    path('departments/<uuid:pk>/toggle-active/', department.DepartmentToggleActiveView.as_view(), name='department_toggle_active'),
    path('departments/export/', department.DepartmentExportView.as_view(), name='department_export'),
        
        
        
        
    
    path('dashboard/', views.HRDashboardView.as_view(), name='hr_dashboard'),
    
    
    
    
    # Staff
    # path('staff/', views.StaffListView.as_view(), name='staff_list'),
    # path('staff/<uuid:pk>/', views.StaffDetailView.as_view(), name='staff_detail'),
    
    # Leave Management
    # path('leave-applications/', views.LeaveApplicationListView.as_view(), name='leave_application_list'),
    # path('leave-applications/add/', views.LeaveApplicationCreateView.as_view(), name='leave_application_add'),
    # path('leave-applications/<uuid:pk>/review/', views.LeaveApplicationUpdateView.as_view(), name='leave_application_review'),
    
    
    # Payroll
   #  path('payroll/', views.PayrollListView.as_view(), name='payroll_list'),
   #  path('payroll/generate/', views.GeneratePayrollView.as_view(), name='generate_payroll'),
]