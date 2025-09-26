from django.urls import path
from . import views

app_name = 'examination'

urlpatterns = [
    # Exam Type URLs
    path('exam-types/', views.ExamTypeListView.as_view(), name='exam_type_list'),
    path('exam-types/create/', views.ExamTypeCreateView.as_view(), name='exam_type_create'),
    path('exam-types/<uuid:pk>/edit/', views.ExamTypeUpdateView.as_view(), name='exam_type_update'),
    path('exam-types/<uuid:pk>/delete/', views.ExamTypeDeleteView.as_view(), name='exam_type_delete'),
    path('exam-types/export/', views.ExamTypeExportView.as_view(), name='exam_type_export'),
    
    # Exam URLs
    path('exams/', views.ExamListView.as_view(), name='exam_list'),
    path('exams/create/', views.ExamCreateView.as_view(), name='exam_create'),
    path('exams/<uuid:pk>/', views.ExamDetailView.as_view(), name='exam_detail'),
    path('exams/<uuid:pk>/edit/', views.ExamUpdateView.as_view(), name='exam_update'),
    path('exams/<uuid:pk>/delete/', views.ExamDeleteView.as_view(), name='exam_delete'),
    path('exams/export/', views.ExamExportView.as_view(), name='exam_export'),
    
    # Exam Subject URLs
    path('exam-subjects/', views.ExamSubjectListView.as_view(), name='exam_subject_list'),
    path('exam-subjects/create/', views.ExamSubjectCreateView.as_view(), name='exam_subject_create'),
    path('exam-subjects/<uuid:pk>/', views.ExamSubjectDetailView.as_view(), name='exam_subject_detail'),
    path('exam-subjects/<uuid:pk>/edit/', views.ExamSubjectUpdateView.as_view(), name='exam_subject_update'),
    path('exam-subjects/<uuid:pk>/delete/', views.ExamSubjectDeleteView.as_view(), name='exam_subject_delete'),
    path('exam-subjects/export/', views.ExamSubjectExportView.as_view(), name='exam_subject_export'),
    
    # Exam Result URLs
    path('results/', views.ExamResultListView.as_view(), name='exam_result_list'),
    path('results/create/', views.ExamResultCreateView.as_view(), name='exam_result_create'),
    path('results/<uuid:pk>/', views.ExamResultDetailView.as_view(), name='exam_result_detail'),

    path('results/<uuid:pk>/edit/', views.ExamResultUpdateView.as_view(), name='exam_result_update'),
    path('results/<uuid:pk>/delete/', views.ExamResultDeleteView.as_view(), name='exam_result_delete'),
    path('results/export/', views.ExamResultExportView.as_view(), name='exam_result_export'),
    # path("exam-results/<uuid:pk>/export/", views.ExamResultDetailExportView.as_view(),name="exam_result_detail_export",),
    path( 'exam-results/<uuid:pk>/report-card/', views.ExamResultReportCardExportView.as_view(), name='exam_result_report_card'),
    path('dashboard/', views.ExamDashboardView.as_view(), name='dashboard'),
]