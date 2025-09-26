from django import forms
from .models import ItemCategory, Item, PurchaseOrder, PurchaseOrderItem, StockTransaction
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils import timezone


class ItemCategoryForm(forms.ModelForm):
    class Meta:
        model = ItemCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter category description'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'category', 'description', 'quantity', 'min_quantity', 'unit', 'price', 'location']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter item name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter item description'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'min_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit': forms.NumberInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter storage location'}),
        }


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'order_date', 'expected_delivery', 'notes']
        widgets = {
            'supplier': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter supplier name'
            }),
            'order_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'expected_delivery': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes or instructions'
            }),
        }

class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['item', 'quantity', 'unit_price']
        widgets = {
            'item': forms.Select(attrs={
                'class': 'form-select item-select',
                'data-live-search': 'true'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control quantity-input',
                'min': 1,
                'step': 1
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control unit-price-input',
                'min': 0,
                'step': '0.01'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        
        if self.institution:
            self.fields['item'].queryset = Item.objects.filter(
                institution=self.institution
            ).order_by('name')

PurchaseOrderItemFormSet = forms.inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)



class PurchaseOrderStatusForm(forms.ModelForm):
    reason_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Reason for rejection or cancellation...'
        }),
        label="Reason"
    )
    
    order_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Order Date"
    )

    class Meta:
        model = PurchaseOrder
        fields = ['status', 'received_date', 'approved_by', 'notes']
        widgets = {
            'status': forms.HiddenInput(),  # We'll handle this with custom radio buttons
            'received_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'approved_by': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes about this status change...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter approved_by to staff users only
        self.fields['approved_by'].queryset = User.objects.filter(
            is_staff=True
        ).order_by('first_name', 'last_name')
        
        # Set initial received date to today
        self.fields['received_date'].initial = timezone.now().date()
        
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        received_date = cleaned_data.get('received_date')
        reason_notes = cleaned_data.get('reason_notes')
        
        # Validate received date for received status
        if status == 'received' and not received_date:
            raise forms.ValidationError({
                'received_date': 'Received date is required when marking as received.'
            })
        
        # Validate reason for rejection/cancellation
        if status in ['rejected', 'cancelled'] and not reason_notes:
            raise forms.ValidationError({
                'reason_notes': 'Reason is required for rejection or cancellation.'
            })
            
        return cleaned_data

class ItemFilterForm(forms.Form):
    CATEGORY_CHOICES = [
        ('', 'All Categories'),
        ('stationery', 'Stationery'),
        ('electronics', 'Electronics'),
        ('furniture', 'Furniture'),
        ('cleaning', 'Cleaning Supplies'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
    ]

    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Search items...'
    }))
    
    category = forms.ChoiceField(choices=CATEGORY_CHOICES, required=False, widget=forms.Select(attrs={
        'class': 'form-select'
    }))
    
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False, widget=forms.Select(attrs={
        'class': 'form-select'
    }))



class StockTransactionForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ['item', 'transaction_type', 'quantity', 'reference', 'notes']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reference number'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter transaction notes'}),
        }

    def __init__(self, *args, institution=None, **kwargs):
        super().__init__(*args, **kwargs)
        if institution:
            self.fields['item'].queryset = Item.objects.filter(institution=institution)

class InventoryFilterForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Search items...'
    }))
    category = forms.ModelChoiceField(
        queryset=ItemCategory.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status'), ('in_stock', 'In Stock'), ('low_stock', 'Low Stock'), ('out_of_stock', 'Out of Stock')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        if institution:
            self.fields['category'].queryset = ItemCategory.objects.filter(institution=institution, is_active=True)