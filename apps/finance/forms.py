
import uuid
from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import FeeStructure, FeeInvoice, Payment
from apps.academics.models import AcademicYear, Class


class FeeStructureForm(forms.ModelForm):
    class Meta:
        model = FeeStructure
        # Remove 'institution' from fields so user cannot edit it
        fields = ['name', 'academic_year', 'class_name', 'amount', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Enter fee structure name')}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'class_name': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'class_name': _('Class'),
            'is_active': _('Active'),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Expect logged-in user
        super().__init__(*args, **kwargs)

        # Filter academic_year and class_name by user's institution
        if user and hasattr(user, 'profile') and user.profile.institution:
            institution = user.profile.institution
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(institution=institution)
            self.fields['class_name'].queryset = Class.objects.filter(institution=institution, is_active=True)
        else:
            # No institution detected, empty queryset
            self.fields['academic_year'].queryset = AcademicYear.objects.none()
            self.fields['class_name'].queryset = Class.objects.none()


class FeeInvoiceForm(forms.ModelForm):
    class Meta:
        model = FeeInvoice
        fields = ['institution', 'student', 'academic_year', 'issue_date', 'due_date', 'total_amount', 'status']
        widgets = {
            'institution': forms.Select(attrs={'class': 'form-select'}),
            'student': forms.Select(attrs={'class': 'form-select'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial values
        self.fields['issue_date'].initial = timezone.now().date()
        self.fields['due_date'].initial = timezone.now().date() + timezone.timedelta(days=30)
        
        # If editing an existing invoice, don't allow changing some fields
        if self.instance and self.instance.pk:
            self.fields['institution'].disabled = True
            self.fields['student'].disabled = True
            self.fields['academic_year'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        issue_date = cleaned_data.get('issue_date')
        due_date = cleaned_data.get('due_date')
        
        if issue_date and due_date and due_date < issue_date:
            raise forms.ValidationError(_('Due date cannot be before issue date.'))
        
        return cleaned_data

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            'student', 'invoice', 'payment_mode',
            'payment_date', 'reference_number', 'amount',
            'amount_paid', 'status', 'remarks',
        ]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select', 'id': 'id_student'}),
            'invoice': forms.Select(attrs={'class': 'form-select', 'id': 'id_invoice'}),
            'payment_mode': forms.Select(attrs={'class': 'form-select'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Reference number')}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'id': 'id_amount', 'readonly': 'readonly'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'id': 'id_amount_paid'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Additional remarks')}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fields['payment_date'].initial = timezone.now().date()
        
        # Make amount field read-only always
        self.fields['amount'].widget.attrs['readonly'] = True
        self.fields['amount'].widget.attrs['disabled'] = True
        
        # For existing payments, make student and invoice read-only too
        if self.instance and self.instance.pk:
            self.fields['student'].widget.attrs['readonly'] = True
            self.fields['student'].widget.attrs['disabled'] = True
            self.fields['invoice'].widget.attrs['disabled'] = True
            self.fields['invoice'].widget.attrs['readonly'] = True
        
        # Set initial values from invoice if provided
        invoice_id = self.data.get('invoice') or (self.instance.invoice_id if self.instance else None)
        if invoice_id:
            try:
                invoice = FeeInvoice.objects.get(id=invoice_id)
                if not self.instance.pk:  # Only for new payments
                    self.fields['student'].initial = invoice.student
                    balance = invoice.total_amount - invoice.paid_amount
                    self.initial['amount'] = balance
                    self.initial['amount_paid'] = balance
            except FeeInvoice.DoesNotExist:
                pass

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        amount_paid = cleaned_data.get('amount_paid')
        status = cleaned_data.get('status')
        invoice = cleaned_data.get('invoice')

        # Validate amount paid vs amount
        if amount_paid and amount and amount_paid > amount:
            raise forms.ValidationError(_('Amount paid cannot be greater than total amount.'))

        # For new payments, validate invoice balance
        if not self.instance.pk and invoice and amount:
            available_balance = invoice.total_amount - invoice.paid_amount
            if amount > available_balance:
                raise forms.ValidationError(
                    _('Payment amount (%(amount)s) exceeds invoice balance (%(balance)s).') % {
                        'amount': amount,
                        'balance': available_balance
                    }
                )

        # Validate status transitions for existing payments
        if self.instance and self.instance.pk:
            old_status = self.instance.status
            new_status = status
            if old_status in ['completed', 'paid', 'refunded', 'cancelled'] and new_status != old_status:
                raise forms.ValidationError(
                    _('Cannot change status from %(old_status)s to %(new_status)s.') % {
                        'old_status': self.instance.get_status_display(),
                        'new_status': dict(self.fields['status'].choices).get(new_status, new_status)
                    }
                )

        return cleaned_data

    def save(self, commit=True):
        """Always set institution from request"""
        obj = super().save(commit=False)
        
        if self.request:
            if hasattr(self.request, "institution"):
                obj.institution = self.request.institution
            else:
                from apps.core.utils import get_user_institution
                institution = get_user_institution(self.request.user, self.request)
                if institution:
                    obj.institution = institution
        
        if commit:
            obj.save()
        return obj

class PaymentSearchForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Student')
    )
    invoice = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Invoice')
    )
    status = forms.ChoiceField(
        choices=[('', _('All Statuses'))] + list(Payment.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Status')
    )
    payment_mode = forms.ChoiceField(
        choices=[('', _('All Modes'))] + list(Payment.MODE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Payment Mode')
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label=_('From Date')
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label=_('To Date')
    )

    def __init__(self, *args, **kwargs):
        institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        # Limit querysets to the current institution
        if institution:
            from apps.students.models import Student
            self.fields['student'].queryset = Student.objects.filter(institution=institution)
            self.fields['invoice'].queryset = FeeInvoice.objects.filter(institution=institution)


class FeeInvoiceSearchForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Student')
    )
    academic_year = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Academic Year')
    )
    status = forms.ChoiceField(
        choices=[('', _('All Statuses'))] + list(FeeInvoice.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Status')
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label=_('From Date')
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label=_('To Date')
    )

    def __init__(self, *args, **kwargs):
        institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        # Limit querysets to the current institution
        if institution:
            from apps.students.models import Student
            from apps.academics.models import AcademicYear
            self.fields['student'].queryset = Student.objects.filter(institution=institution)
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(institution=institution)