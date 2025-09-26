from django.urls import path
from . import views
from . import export
urlpatterns = [
    path('', views.TeacherListView.as_view(), name='teacher_list'),
    path('add/', views.TeacherCreateView.as_view(), name='teacher_add'),
    path('<uuid:pk>/', views.TeacherDetailView.as_view(), name='teacher_detail'),
    path('<uuid:pk>/edit/', views.TeacherUpdateView.as_view(), name='teacher_edit'),
    path('<uuid:pk>/delete/', views.TeacherDeleteView.as_view(), name='teacher_delete'),
    
    # path('export/csv/', views.ExportTeachersCSVView.as_view(), name='export_teachers_csv'),
    path('export/', export.TeacherExportView.as_view(), name='export_teachers'),
    path('<uuid:pk>/export/detail/', export.TeacherExportDetailView.as_view(), name='export_teacher_detail'),
    
    path('<uuid:pk>/id-card/', views.teacher_id_card_png, name='teacher_id_card_default'),

]