from django.urls import path
from . import views
from . import invoices
from . import payments
from . import reports

app_name = "finance"

urlpatterns = [
    # Fee Structure
    path('fee-structure/', views.FeeStructureListView.as_view(), name='fee_structure_list'),
    path('fee-structure/add/', views.FeeStructureCreateView.as_view(), name='fee_structure_add'),
    path("fee-structures/<uuid:pk>/", views.FeeStructureDetailView.as_view(), name="fee_structure_detail"),
    path('fee-structure/<uuid:pk>/edit/', views.FeeStructureUpdateView.as_view(), name='fee_structure_update'),
    path('fee-structure/<uuid:pk>/delete/', views.FeeStructureDeleteView.as_view(), name='fee_structure_delete'),
   
    # path('fee-structure/<uuid:pk>/disable/', views.FeeStructureDisableView.as_view(), name='fee_structure_disable'),
   
    path('fee-structures/export/', views.fee_structure_export_pdf, name='fee_structure_export'),
    path('fee-structures/<uuid:pk>/disable/', views.FeeStructureDisableView.as_view(), name='fee_structure_disable'),
    path('fee-structures/<uuid:pk>/enable/', views.FeeStructureEnableView.as_view(), name='fee_structure_enable'),

    # Fee Invoices
    path('invoices/', invoices.FeeInvoiceListView.as_view(), name='fee_invoice_list'),
    path('invoices/create/', invoices.FeeInvoiceCreateView.as_view(), name='fee_invoice_create'),
    path('invoices/<uuid:pk>/',invoices.FeeInvoiceDetailView.as_view(), name='fee_invoice_detail'),
    path('invoices/<uuid:pk>/edit/', invoices.FeeInvoiceUpdateView.as_view(), name='fee_invoice_update'),
    path('invoices/<uuid:pk>/delete/',invoices.FeeInvoiceDeleteView.as_view(), name='fee_invoice_delete'),
    path('invoices/ajax/get-students/', invoices.get_students_by_class, name='ajax_get_students'),
    path('invoices/export/', invoices.fee_invoice_list_export, name='fee_invoice_export'),
    path('invoice/<uuid:pk>/export/', invoices.fee_invoice_detail_export, name='fee_invoice_export_detail'),
    # Payments
    path('payments/', payments.PaymentListView.as_view(), name='payment_list'),
    path('payments/add/', payments.PaymentCreateView.as_view(), name='payment_create'),
    path('payments/<uuid:pk>/',payments.PaymentDetailView.as_view(), name='payment_detail'),
    path('payments/<uuid:pk>/edit/', payments.PaymentUpdateView.as_view(), name='payment_update'),
    path('payments/<uuid:pk>/delete/', payments.PaymentDeleteView.as_view(), name='payment_delete'),
    path('payments/export/', payments.payment_list_export, name='payment_export'),
    path('payments/<uuid:pk>/export/', payments.payment_detail_export, name='payment_detail_export'),

    # path('payments/<uuid:pk>/receipt/',payments.PaymentReceiptView.as_view(), name='payment_receipt_pdf'),
    path('payments/<uuid:pk>/refund/', payments.PaymentRefundView.as_view(), name='payment_refund'),
    # path('payments/export/', payments.PaymentExportView.as_view(), name='payment_export'),
    path('ajax/invoice/<uuid:pk>/', payments.InvoiceAjaxView.as_view(), name='invoice_ajax'),
    path('ajax/student/<uuid:student_id>/invoices/', payments.StudentInvoicesAjaxView.as_view(), name='student_invoices_api'),
    # Reports
    path('reports/collection/', reports.FeeCollectionReportView.as_view(), name='fee_collection_report'),
    path('reports/outstanding/',reports.OutstandingFeeReportView.as_view(), name='outstanding_fee_report'),
    
    # AJAX endpoints
    path('ajax/students-for-fee-structure/',reports.GetStudentsForFeeStructureView.as_view(), name='ajax_students_for_fee_structure'),
    path('ajax/invoice-balance/', reports.GetInvoiceBalanceView.as_view(), name='ajax_invoice_balance'),
]