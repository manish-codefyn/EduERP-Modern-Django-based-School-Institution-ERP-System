import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings


class PaymentGateway(models.Model):
    GATEWAY_CHOICES = (
        ('razorpay', 'Razorpay'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('instamojo', 'Instamojo'),
        ('paytm', 'PayTM'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    gateway_name = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    is_active = models.BooleanField(default=False)
    test_mode = models.BooleanField(default=True)
    
    # Credentials (should be encrypted in production)
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    merchant_id = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments_gateway'
        unique_together = ['institution', 'gateway_name']
    
    def __str__(self):
        return f"{self.get_gateway_name_display()} - {self.institution}"

class OnlinePayment(models.Model):
    STATUS_CHOICES = (
        ('created', 'Created'),
        ('attempted', 'Attempted'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    payment = models.ForeignKey('finance.Payment', on_delete=models.CASCADE, related_name='online_payments')
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.CASCADE)
    gateway_payment_id = models.CharField(max_length=255, blank=True)
    gateway_order_id = models.CharField(max_length=255, blank=True)
    gateway_signature = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='created')
    gateway_response = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments_online_payment'
    
    def __str__(self):
        return f"Online Payment #{self.payment.payment_number}"

class PaymentWebhookLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.CASCADE)
    webhook_id = models.CharField(max_length=255, blank=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    headers = models.JSONField()
    signature = models.CharField(max_length=500, blank=True)
    processed = models.BooleanField(default=False)
    processing_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payments_webhook_log'
    
    def __str__(self):
        return f"Webhook {self.event_type} - {self.gateway}"

class Refund(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    online_payment = models.ForeignKey(OnlinePayment, on_delete=models.CASCADE)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    gateway_refund_id = models.CharField(max_length=255, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    gateway_response = models.JSONField(default=dict)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments_refund'
    
    def __str__(self):
        return f"Refund for {self.online_payment} - {self.refund_amount}"
    

