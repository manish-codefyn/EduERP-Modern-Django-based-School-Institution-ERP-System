# finance/views.py
from django.views.generic import CreateView, UpdateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from .models import FeeStructure, FeeInvoice, Payment
from .forms import FeeStructureForm, FeeInvoiceForm, PaymentForm, PaymentSearchForm, FeeInvoiceSearchForm


class FeeStructureCreateView(LoginRequiredMixin, CreateView):
    model = FeeStructure
    form_class = FeeStructureForm
    template_name = 'finance/fee_structure_form.html'
    success_url = '/finance/fee-structures/'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Set initial institution based on user's institution
        kwargs['initial'] = {'institution': self.request.user.institution}
        return kwargs


class FeeInvoiceCreateView(LoginRequiredMixin, CreateView):
    model = FeeInvoice
    form_class = FeeInvoiceForm
    template_name = 'finance/fee_invoice_form.html'
    success_url = '/finance/invoices/'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {'institution': self.request.user.institution}
        return kwargs


class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'finance/payment_form.html'
    success_url = '/finance/payments/'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {'institution': self.request.user.institution}
        return kwargs


class PaymentListView(LoginRequiredMixin, ListView):
    model = Payment
    template_name = 'finance/payment_list.html'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(institution=self.request.user.institution)
        form = PaymentSearchForm(self.request.GET, institution=self.request.user.institution)
        
        if form.is_valid():
            student = form.cleaned_data.get('student')
            invoice = form.cleaned_data.get('invoice')
            status = form.cleaned_data.get('status')
            payment_mode = form.cleaned_data.get('payment_mode')
            start_date = form.cleaned_data.get('start_date')
            end_date = form.cleaned_data.get('end_date')
            
            if student:
                queryset = queryset.filter(student=student)
            if invoice:
                queryset = queryset.filter(invoice=invoice)
            if status:
                queryset = queryset.filter(status=status)
            if payment_mode:
                queryset = queryset.filter(payment_mode=payment_mode)
            if start_date:
                queryset = queryset.filter(payment_date__gte=start_date)
            if end_date:
                queryset = queryset.filter(payment_date__lte=end_date)
        
        return queryset.order_by('-payment_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = PaymentSearchForm(
            self.request.GET, 
            institution=self.request.user.institution
        )
        return context