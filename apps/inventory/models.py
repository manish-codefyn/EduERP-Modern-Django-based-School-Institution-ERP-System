import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.text import slugify


class ItemCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)  # <-- slug field
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_item_category'
        unique_together = ['institution', 'name']
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while ItemCategory.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Item(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)  # <-- slug field
    category = models.ForeignKey(ItemCategory, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    quantity = models.IntegerField(default=0)
    min_quantity = models.IntegerField(default=5)
    unit = models.CharField(max_length=20, default='pcs')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_item'
    
    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"
    
    def save(self, *args, **kwargs):
        if not self.slug:  # generate slug only if missing
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Item.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
        
    @property
    def status(self):
        if self.quantity <= 0:
            return 'out_of_stock'
        elif self.quantity <= self.min_quantity:
            return 'low_stock'
        else:
            return 'in_stock'

class StockTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('purchase', 'Purchase'),
        ('issue', 'Issue'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
        ('damage', 'Damage'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    previous_quantity = models.IntegerField()
    new_quantity = models.IntegerField()
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    transaction_date = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey('users.User', on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'inventory_stock_transaction'
    
    def __str__(self):
        return f"{self.item.name} - {self.get_transaction_type_display()} - {self.quantity}"
    
    def save(self, *args, **kwargs):
        self.previous_quantity = self.item.quantity
        
        if self.transaction_type == 'purchase':
            self.item.quantity += self.quantity
        elif self.transaction_type in ['issue', 'damage']:
            self.item.quantity -= self.quantity
        elif self.transaction_type == 'return':
            self.item.quantity += self.quantity
        
        self.new_quantity = self.item.quantity
        self.item.save()
        super().save(*args, **kwargs)

class PurchaseOrder(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('organization.Institution', on_delete=models.CASCADE)
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.CharField(max_length=200)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    order_date = models.DateField(null=True, blank=True)
    expected_delivery = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='created_purchase_orders')
    approved_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_purchase_orders')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_purchase_order'
    
    def __str__(self):
        return f"PO-{self.po_number}"
    
    def save(self, *args, **kwargs):
        if not self.po_number:
            year = timezone.now().year
            last_po = PurchaseOrder.objects.filter(
                institution=self.institution,
                po_number__startswith=f"PO-{year}-"
            ).order_by('-po_number').first()
            
            if last_po:
                last_num = int(last_po.po_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
                
            self.po_number = f"PO-{year}-{new_num:04d}"
        
        super().save(*args, **kwargs)

class PurchaseOrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'inventory_purchase_order_item'
    
    def __str__(self):
        return f"{self.item.name} - {self.quantity}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        
        # Update purchase order total amount
        self.purchase_order.total_amount = self.purchase_order.items.aggregate(
            total=models.Sum('total_price')
        )['total'] or 0
        self.purchase_order.save()