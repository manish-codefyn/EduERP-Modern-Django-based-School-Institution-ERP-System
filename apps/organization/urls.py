from django.urls import path
from .import views 
from .import compliance 
from .import affiliation_views
from .import accreditation_views
from .import partnership_views

app_name = 'organization'

urlpatterns = [

    path('', views.OrganizationDashboardView.as_view(), name='dashboard'),


   
    path('institutions/', views.InstitutionListView.as_view(), name='institution_list'),
    path('institutions/add/', views.InstitutionCreateView.as_view(), name='institution_create'),
    path('institutions/<uuid:pk>/', views.InstitutionDetailView.as_view(), name='institution_detail'),
    path('institutions/<uuid:pk>/edit/', views.InstitutionUpdateView.as_view(), name='institution_update'),
    path('institutions/<uuid:pk>/delete/', views.InstitutionDeleteView.as_view(), name='institution_delete'),
    # Export URL
    path('institutions/export/', views.InstitutionExportView.as_view(), name='institution_export'),

    # Department URLs
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('departments/add/', views.DepartmentCreateView.as_view(), name='department_create'),
    path('departments/<uuid:pk>/edit/', views.DepartmentUpdateView.as_view(), name='department_update'),
    path('departments/<uuid:pk>/delete/', views.DepartmentDeleteView.as_view(), name='department_delete'),

    # Branch URLs
    path('branches/', views.BranchListView.as_view(), name='branch_list'),
    path('branches/add/', views.BranchCreateView.as_view(), name='branch_create'),

    path('compliances/', compliance.InstitutionComplianceListView.as_view(), name='compliance_list'),
    path('compliances/new/', compliance.InstitutionComplianceCreateView.as_view(), name='compliance_create'),
    path('compliances/<uuid:pk>/edit/', compliance.InstitutionComplianceUpdateView.as_view(), name='compliance_update'),
    path('compliances/<uuid:pk>/', compliance.InstitutionComplianceDetailView.as_view(), name='compliance_detail'),
    path('compliances/<uuid:pk>/delete/', compliance.InstitutionComplianceDeleteView.as_view(), name='compliance_delete'),
    path('compliances/export/', compliance.InstitutionComplianceExportView.as_view(), name='compliance_export'),

 # Affiliation URLs
    path('affiliations/', affiliation_views.AffiliationListView.as_view(), name='affiliation_list'),
    path('affiliations/create/', affiliation_views.AffiliationCreateView.as_view(), name='affiliation_create'),
    path('affiliations/<uuid:pk>/', affiliation_views.AffiliationDetailView.as_view(), name='affiliation_detail'),
    path('affiliations/<uuid:pk>/update/', affiliation_views.AffiliationUpdateView.as_view(), name='affiliation_update'),
    path('affiliations/<uuid:pk>/delete/', affiliation_views.AffiliationDeleteView.as_view(), name='affiliation_delete'),
    path('affiliations/export/', affiliation_views.AffiliationExportView.as_view(), name='affiliation_export'),


    # Accreditation URLs
    path('accreditations/', accreditation_views.AccreditationListView.as_view(), name='accreditation_list'),
    path('accreditations/create/', accreditation_views.AccreditationCreateView.as_view(), name='accreditation_create'),
    path('accreditations/<uuid:pk>/', accreditation_views.AccreditationDetailView.as_view(), name='accreditation_detail'),
    path('accreditations/<uuid:pk>/update/', accreditation_views.AccreditationUpdateView.as_view(), name='accreditation_update'),
    path('accreditations/<uuid:pk>/delete/', accreditation_views.AccreditationDeleteView.as_view(), name='accreditation_delete'),
    path('accreditations/export/', accreditation_views.AccreditationExportView.as_view(), name='accreditation_export'),


    path('partnerships/', partnership_views.PartnershipListView.as_view(), name='partnership_list'),
    path('partnerships/create/', partnership_views.PartnershipCreateView.as_view(), name='partnership_create'),
    path('partnerships/<uuid:pk>/', partnership_views.PartnershipDetailView.as_view(), name='partnership_detail'),
    path('partnerships/<uuid:pk>/update/', partnership_views.PartnershipUpdateView.as_view(), name='partnership_update'),
    path('partnerships/<uuid:pk>/delete/', partnership_views.PartnershipDeleteView.as_view(), name='partnership_delete'),
    path('partnerships/export/', partnership_views.PartnershipExportView.as_view(), name='partnership_export'),

]
