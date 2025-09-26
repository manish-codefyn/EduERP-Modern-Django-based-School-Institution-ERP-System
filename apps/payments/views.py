from django.shortcuts import render, get_object_or_404,redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import razorpay
from decimal import Decimal

from .models import PaymentGateway, OnlinePayment, PaymentWebhookLog, Refund
from apps.finance.models import Payment

class PaymentGatewayListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = PaymentGateway
    template_name = 'payments/gateway_list.html'
    permission_required = 'payments.view_paymentgateway'
    context_object_name = 'gateways'
    
    def get_queryset(self):
        return PaymentGateway.objects.filter(school=self.request.school)

class PaymentGatewayUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = PaymentGateway
    fields = ['is_active', 'test_mode', 'api_key', 'api_secret', 'webhook_secret', 'merchant_id']
    template_name = 'payments/gateway_form.html'
    permission_required = 'payments.change_paymentgateway'
    success_url = reverse_lazy('payment_gateway_list')
    
    def get_queryset(self):
        return PaymentGateway.objects.filter(school=self.request.school)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'{self.object.get_gateway_name_display()} settings updated successfully.')
        return response

class OnlinePaymentListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = OnlinePayment
    template_name = 'payments/online_payment_list.html'
    permission_required = 'payments.view_onlinepayment'
    context_object_name = 'online_payments'
    
    def get_queryset(self):
        return OnlinePayment.objects.filter(school=self.request.school).select_related('payment', 'gateway')

@method_decorator(csrf_exempt, name='dispatch')
class CreateRazorpayOrderView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            payment_id = data.get('payment_id')
            
            payment = get_object_or_404(Payment, id=payment_id, school=request.school)
            
            # Get Razorpay gateway configuration
            gateway = PaymentGateway.objects.get(
                school=request.school,
                gateway_name='razorpay',
                is_active=True
            )
            
            # Initialize Razorpay client
            client = razorpay.Client(auth=(gateway.api_key, gateway.api_secret))
            
            # Create order
            order_data = {
                'amount': int(payment.amount * 100),  # Amount in paise
                'currency': 'INR',
                'receipt': payment.payment_number,
                'notes': {
                    'payment_id': str(payment.id),
                    'school_id': str(request.school.id),
                }
            }
            
            order = client.order.create(order_data)
            
            # Create online payment record
            online_payment = OnlinePayment.objects.create(
                school=request.school,
                payment=payment,
                gateway=gateway,
                gateway_order_id=order['id'],
                amount=payment.amount,
                currency='INR',
                status='created'
            )
            
            return JsonResponse({
                'success': True,
                'order_id': order['id'],
                'amount': order['amount'],
                'currency': order['currency'],
                'key': gateway.api_key,
                'online_payment_id': str(online_payment.id)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

@method_decorator(csrf_exempt, name='dispatch')
class VerifyRazorpayPaymentView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            online_payment_id = data.get('online_payment_id')
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_signature = data.get('razorpay_signature')
            
            online_payment = get_object_or_404(
                OnlinePayment, 
                id=online_payment_id, 
                school=request.school
            )
            
            gateway = online_payment.gateway
            client = razorpay.Client(auth=(gateway.api_key, gateway.api_secret))
            
            # Verify payment signature
            params_dict = {
                'razorpay_order_id': online_payment.gateway_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            client.utility.verify_payment_signature(params_dict)
            
            # Update online payment status
            online_payment.gateway_payment_id = razorpay_payment_id
            online_payment.gateway_signature = razorpay_signature
            online_payment.status = 'paid'
            online_payment.save()
            
            # Update main payment status
            online_payment.payment.status = 'completed'
            online_payment.payment.save()
            
            return JsonResponse({'success': True, 'message': 'Payment verified successfully'})
            
        except Exception as e:
            online_payment.status = 'failed'
            online_payment.save()
            return JsonResponse({'success': False, 'error': str(e)})

@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(View):
    def post(self, request):
        try:
            # Verify webhook signature
            signature = request.headers.get('X-Razorpay-Signature')
            body = request.body.decode('utf-8')
            
            # Log webhook
            webhook_log = PaymentWebhookLog.objects.create(
                school=request.school,  # You might need to determine school from payload
                gateway=PaymentGateway.objects.get(gateway_name='razorpay'),
                event_type=request.headers.get('X-Razorpay-Event'),
                payload=json.loads(body),
                headers=dict(request.headers),
                signature=signature
            )
            
            # Process webhook based on event type
            payload = json.loads(body)
            event = payload.get('event')
            
            if event == 'payment.captured':
                payment_id = payload['payload']['payment']['entity']['id']
                online_payment = OnlinePayment.objects.get(gateway_payment_id=payment_id)
                online_payment.status = 'paid'
                online_payment.save()
                
                # Update main payment
                online_payment.payment.status = 'completed'
                online_payment.payment.save()
                
                webhook_log.processed = True
                webhook_log.processing_notes = 'Payment captured successfully'
                
            elif event == 'payment.failed':
                payment_id = payload['payload']['payment']['entity']['id']
                online_payment = OnlinePayment.objects.get(gateway_payment_id=payment_id)
                online_payment.status = 'failed'
                online_payment.save()
                
                webhook_log.processed = True
                webhook_log.processing_notes = 'Payment failed'
            
            webhook_log.save()
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

class RefundCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'payments.add_refund'
    
    def post(self, request, online_payment_id):
        try:
            online_payment = get_object_or_404(
                OnlinePayment, 
                id=online_payment_id, 
                school=request.school,
                status='paid'
            )
            
            refund_amount = Decimal(request.POST.get('refund_amount'))
            reason = request.POST.get('reason')
            
            if refund_amount > online_payment.amount:
                messages.error(request, 'Refund amount cannot exceed original payment amount')
                return redirect('online_payment_list')
            
            # Create refund record
            refund = Refund.objects.create(
                school=request.school,
                online_payment=online_payment,
                refund_amount=refund_amount,
                reason=reason,
                created_by=request.user
            )
            
            # Process refund through gateway
            if online_payment.gateway.gateway_name == 'razorpay':
                client = razorpay.Client(auth=(
                    online_payment.gateway.api_key, 
                    online_payment.gateway.api_secret
                ))
                
                refund_data = client.payment.refund(
                    online_payment.gateway_payment_id,
                    {'amount': int(refund_amount * 100)}
                )
                
                refund.gateway_refund_id = refund_data['id']
                refund.status = 'processed'
                refund.save()
                
                # Update online payment status
                online_payment.status = 'refunded'
                online_payment.save()
                
                # Update main payment
                online_payment.payment.status = 'refunded'
                online_payment.payment.save()
                
                messages.success(request, 'Refund processed successfully')
            else:
                messages.info(request, 'Refund record created. Manual processing required for this gateway.')
            
            return redirect('online_payment_list')
            
        except Exception as e:
            messages.error(request, f'Error processing refund: {str(e)}')
            return redirect('online_payment_list')