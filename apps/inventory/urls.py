from django.urls import path
from . import views
from . import exports

app_name = 'inventory'

urlpatterns = [
    # Dashboard
    path('', views.InventoryDashboardView.as_view(), name='dashboard'),
    
    # Categories
    path('categories/', views.ItemCategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.ItemCategoryCreateView.as_view(), name='category_create'),
    path('categories/<uuid:pk>/update/', views.ItemCategoryUpdateView.as_view(), name='category_update'),
    path('categories/<uuid:pk>/delete/', views.ItemCategoryDeleteView.as_view(), name='category_delete'),
    
    # Items
    path('items/', views.ItemListView.as_view(), name='item_list'),
    path('items/create/', views.ItemCreateView.as_view(), name='item_create'),
    path('items/<uuid:pk>/update/', views.ItemUpdateView.as_view(), name='item_update'),
    path('items/<uuid:pk>/delete/', views.ItemUpdateView.as_view(), name='item_delete'),
    path('items/<uuid:pk>/', views.ItemDetailView.as_view(), name='item_detail'),
    
    # Transactions

  # Stock Transaction URLs
    path('transactions/', views.StockTransactionListView.as_view(), name='transaction_list'),
    path('transactions/create/', views.StockTransactionCreateView.as_view(), name='transaction_create'),
    path('transactions/<uuid:pk>/', views.StockTransactionDetailView.as_view(), name='transaction_detail'),
    path('transactions/export/', exports.StockTransactionExportView.as_view(), name='transaction_export'),
    path('transactions/<uuid:pk>/export/', exports.StockTransactionDetailExportView.as_view(), name='transaction_detail_export'),
    # Purchase Order URLs
    path('purchase-orders/', views.PurchaseOrderListView.as_view(), name='purchase_order_list'),
    path('purchase-orders/create/', views.PurchaseOrderCreateView.as_view(), name='purchase_order_create'),
    path('purchase-orders/<uuid:pk>/', views.PurchaseOrderDetailView.as_view(), name='purchase_order_detail'),
    path('purchase-orders/<uuid:pk>/update/', views.PurchaseOrderUpdateView.as_view(), name='purchase_order_update'),
    path('purchase-orders/<uuid:pk>/delete/', views.PurchaseOrderDeleteView.as_view(), name='purchase_order_delete'),
    path('purchase-orders/<uuid:pk>/update-status/', views.PurchaseOrderStatusUpdateView.as_view(), name='purchase_order_status_update'),
    
    # Export URLs
    path('export/', views.InventoryExportView.as_view(), name='export'),
  
    # API URLs for AJAX
    path('api/items/<uuid:pk>/quantity/', views.get_item_quantity, name='api_item_quantity'),

  
]