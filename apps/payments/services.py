import razorpay
from django.conf import settings
from .models import PaymentGateway, OnlinePayment

class PaymentService:
    def __init__(self, school, gateway_name='razorpay'):
        self.school = school
        self.gateway_name = gateway_name
        self.gateway = PaymentGateway.objects.get(school=school, gateway_name=gateway_name)
        self.client = None
        
        if self.gateway.is_active:
            if gateway_name == 'razorpay':
                self.client = razorpay.Client(auth=(
                    self.gateway.api_key, 
                    self.gateway.api_secret
                ))
    
    def create_order(self, payment):
        """Create a payment order with the gateway"""
        if not self.gateway.is_active or not self.client:
            raise Exception("Payment gateway is not active")
        
        # Convert amount to paise (for Razorpay)
        amount = int(float(payment.amount) * 100)
        
        try:
            # Create order with Razorpay
            order_data = {
                'amount': amount,
                'currency': payment.currency,
                'receipt': payment.payment_number,
                'notes': {
                    'school_id': str(self.school.id),
                    'payment_id': str(payment.id),
                }
            }
            
            order = self.client.order.create(order_data)
            
            # Create online payment record
            online_payment = OnlinePayment.objects.create(
                school=self.school,
                payment=payment,
                gateway=self.gateway,
                gateway_order_id=order['id'],
                amount=payment.amount,
                currency=payment.currency,
                status='created'
            )
            
            return {
                'order_id': order['id'],
                'amount': order['amount'],
                'currency': order['currency'],
                'key': self.gateway.api_key,
                'online_payment_id': str(online_payment.id)
            }
            
        except Exception as e:
            raise Exception(f"Failed to create payment order: {str(e)}")
    
    def verify_payment(self, online_payment_id, payment_id, signature):
        """Verify payment signature"""
        try:
            online_payment = OnlinePayment.objects.get(id=online_payment_id)
            params_dict = {
                'razorpay_order_id': online_payment.gateway_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            # Verify payment signature
            self.client.utility.verify_payment_signature(params_dict)
            
            # Update payment status
            online_payment.gateway_payment_id = payment_id
            online_payment.gateway_signature = signature
            online_payment.status = 'paid'
            online_payment.save()
            
            # Update main payment status
            online_payment.payment.status = 'completed'
            online_payment.payment.save()
            
            return True
            
        except Exception as e:
            # Payment verification failed
            online_payment.status = 'failed'
            online_payment.save()
            raise Exception(f"Payment verification failed: {str(e)}")