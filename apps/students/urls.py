from django.urls import path
from . import views
from . import exports

app_name = 'students'

urlpatterns = [
    path('', views.StudentListView.as_view(), name='student_list'),
    path('create/', views.StudentCreateView.as_view(), name='student_create'),
    path('<uuid:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('<uuid:pk>/update/', views.StudentUpdateView.as_view(), name='student_update'),
    path('<uuid:pk>/delete/', views.StudentDeleteView.as_view(), name='student_delete'),
    
    # Onboarding steps
    path('<uuid:pk>/onboarding/', views.StudentOnboardingView.as_view(), name='student_onboarding'),
    
    path('<uuid:pk>/guardian/create/', views.GuardianCreateView.as_view(), name='guardian_create'),
    path('<uuid:pk>/guardian/update/',views.GuardianUpdateView.as_view(), name='guardian_update'),
    
    path('<uuid:pk>/medical/create/', views.MedicalInfoCreateView.as_view(), name='medical_create'),
    path('<uuid:pk>/medical/update/', views.MedicalInfoUpdateView.as_view(), name='medical_update'),
    
    
    path('<uuid:pk>/address/create/', views.AddressCreateView.as_view(), name='address_create'),
    path('<uuid:pk>/address/update/', views.AddressUpdateView.as_view(), name='address_update'),
    
    
    path('<uuid:pk>/document/list/', views.StudentDocumentListView.as_view(), name='document_list'),
    path('<uuid:pk>/document/upload/', views.StudentDocumentUploadView.as_view(), name='document_upload'),
    path('<uuid:student_pk>/document/<uuid:pk>/update/',
    views.StudentDocumentUpdateView.as_view(),
    name="document_update",
     ),
    path(
        "<uuid:student_pk>/document/<uuid:doc_pk>/delete/",
        views.StudentDocumentDeleteView.as_view(),
        name="document_delete"
    ),
    # Quick actions
    path('<uuid:pk>/status/update/', views.StudentStatusUpdateView.as_view(), name='student_status_update'),
    path('<uuid:pk>/class/update/', views.StudentClassUpdateView.as_view(), name='student_class_update'),
    path("ajax/load-sections/", views.load_sections, name="ajax_load_sections"),
    
        # Transport URLs
    path('<uuid:pk>/transport/create/', views.TransportCreateView.as_view(), name='transport_create'),
    path('transport/<uuid:pk>/update/', views.TransportUpdateView.as_view(), name='transport_update'),
    
    # Hostel URLs
    path('<uuid:pk>/hostel/create/', views.HostelCreateView.as_view(), name='hostel_create'),
    path('hostel/<uuid:pk>/update/', views.HostelUpdateView.as_view(), name='hostel_update'),
    
    # Academic History URLs
    path('<uuid:pk>/history/create/', views.HistoryCreateView.as_view(), name='history_create'),
    path('history/<uuid:pk>/update/', views.HistoryUpdateView.as_view(), name='history_update'),
    

    path('export/', exports.StudentExportView.as_view(), name='student_export'),
    path("students/<uuid:pk>/export/pdf/", exports.StudentExportDetailView.as_view(), name="student_detail_export"),
    path("students/<uuid:pk>/id/", views.student_id_card_png, name="student-id-card"),

    path('<uuid:pk>/identification/add/', views.StudentIdentificationCreateView.as_view(), name='identification_create'),
    path('<uuid:pk>/identification/edit/', views.StudentIdentificationUpdateView.as_view(), name='identification_update'),
]