from django.urls import path
from . import views
from . import subject_views
from . import house_views
from . import timetable
from . import ay_views

app_name = "academics"

urlpatterns = [
    
    path('academic-years/', ay_views.AcademicYearListView.as_view(), name='academic_year_list'),
    path('academic-years/add/',  ay_views.AcademicYearCreateView.as_view(), name='academic_year_add'),
    path('academic-years/<uuid:pk>/edit/',  ay_views.AcademicYearUpdateView.as_view(), name='academic_year_edit'),
    path('academic-years/<uuid:pk>/delete/',  ay_views.AcademicYearDeleteView.as_view(), name='academic_year_delete'),
    path('academic-years/export/',  ay_views.export_academic_years, name='academic_year_export'),
    
        # House URLs
    path('houses/', house_views.HouseListView.as_view(), name='house_list'),
    path('houses/create/', house_views.HouseCreateView.as_view(), name='house_create'),
    path('houses/<uuid:pk>/update/', house_views.HouseUpdateView.as_view(), name='house_update'),
    path('houses/<uuid:pk>/delete/',house_views.HouseDeleteView.as_view(), name='house_delete'),
    path("houses/export/", house_views.export_houses, name="export_houses"),
    # Subject URLs
    path('subjects/', subject_views.SubjectListView.as_view(), name='subject_list'),
    path('subjects/create/', subject_views.SubjectCreateView.as_view(), name='subject_create'),
    path('subjects/<uuid:pk>/update/', subject_views.SubjectUpdateView.as_view(), name='subject_update'),
    path('subjects/<uuid:pk>/delete/', subject_views.SubjectDeleteView.as_view(), name='subject_delete'),
    path('subjects/export/', subject_views.export_subjects, name='export-subjects'),
    
    # Classes
    path('classes/', views.ClassListView.as_view(), name='class_list'),
    path('classes/add/', views.ClassCreateView.as_view(), name='class_add'),
    path('classes/<uuid:pk>', views.ClassDetailView.as_view(), name='class_detail'),
    path('classes/<uuid:pk>/edit/', views.ClassUpdateView.as_view(), name='class_update'),

    path('classes/<uuid:pk>/delete/', views.ClassDeleteView.as_view(), name='class_delete'),
    # Subjects
    # path('subjects/', views.SubjectListView.as_view(), name='subject_list'),
    # path('subjects/add/', views.SubjectCreateView.as_view(), name='subject_add'),
    
    # Section URLs
    path('classes/<uuid:class_id>/sections/', views.SectionListView.as_view(), name='section_list'),
    path('classes/<uuid:class_id>/sections/add/', views.SectionCreateView.as_view(), name='section_add'),
    path('sections/<uuid:pk>/edit/', views.SectionUpdateView.as_view(), name='section_edit'),
    path('sections/<uuid:pk>/delete/', views.SectionDeleteView.as_view(), name='section_delete'),
    path('sections/export/', views.export_sections, name='export_sections'),
    
    # Timetable URLs
    path('classes/<uuid:class_id>/timetable/', timetable.TimetableView.as_view(), name='timetable_list'),
    path('timetable/add/', timetable.TimetableCreateView.as_view(), name='timetable_add'),
    path('timetable/<uuid:pk>/edit/', timetable.TimetableUpdateView.as_view(), name='timetable_edit'),
    path('timetable/<uuid:pk>/delete/', timetable.TimetableDeleteView.as_view(), name='timetable_delete'),
    path('timetable/export/', timetable.export_timetable, name='timetable_export'),
    path('classes/<uuid:class_id>/timetable/export/',timetable.export_timetable, name='class_timetable_export'),
    # Report URLs
    path('classes/<uuid:class_id>/report/', views.ClassReportView.as_view(), name='class_report'),
    path('reports/classes/', views.ClassSummaryReportView.as_view(), name='class_summary_report'),
    path("class/<uuid:pk>/report/pdf/", views.ClassReportPDFView.as_view(), name="class_report_pdf"),
    path("classes/export/", views.export_classes, name="export-classes"),
]