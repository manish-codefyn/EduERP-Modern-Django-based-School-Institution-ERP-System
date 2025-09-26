from django.urls import path
from . import views

urlpatterns = [
    # Payment Gateways
    path('gateways/', views.PaymentGatewayListView.as_view(), name='payment_gateway_list'),
    path('gateways/<uuid:pk>/edit/', views.PaymentGatewayUpdateView.as_view(), name='payment_gateway_edit'),
    
    # Online Payments
    path('online-payments/', views.OnlinePaymentListView.as_view(), name='online_payment_list'),
    
    # Razorpay Integration
    path('razorpay/create-order/', views.CreateRazorpayOrderView.as_view(), name='razorpay_create_order'),
    path('razorpay/verify-payment/', views.VerifyRazorpayPaymentView.as_view(), name='razorpay_verify_payment'),
    path('razorpay/webhook/', views.RazorpayWebhookView.as_view(), name='razorpay_webhook'),
    
    # Refunds
    path('refund/<uuid:online_payment_id>/', views.RefundCreateView.as_view(), name='process_refund'),
]