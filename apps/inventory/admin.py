# inventory/admin.py
from django.contrib import admin
from django.db.models import Sum
from .models import (
    ItemCategory, Item, StockTransaction,
    PurchaseOrder, PurchaseOrderItem
)


@admin.register(ItemCategory)
class ItemCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "is_active", "created_at")
    list_filter = ("institution", "is_active")
    search_fields = ("name", "description")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    fields = ("item", "quantity", "unit_price", "total_price")
    readonly_fields = ("total_price",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "institution", "category", "quantity", "min_quantity", "status", "price", "unit", "location")
    list_filter = ("category", "institution")
    search_fields = ("name", "description", "location")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")

    def status(self, obj):
        if obj.quantity <= 0:
            return "❌ Out of Stock"
        elif obj.quantity <= obj.min_quantity:
            return "⚠️ Low Stock"
        return "✅ In Stock"
    status.short_description = "Stock Status"


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ("item", "transaction_type", "quantity", "previous_quantity", "new_quantity", "performed_by", "transaction_date")
    list_filter = ("transaction_type", "institution", "performed_by")
    search_fields = ("item__name", "reference")
    ordering = ("-transaction_date",)
    readonly_fields = ("transaction_date", "previous_quantity", "new_quantity")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("po_number", "institution", "supplier", "status", "total_amount", "order_date", "expected_delivery", "received_date")
    list_filter = ("status", "institution", "supplier")
    search_fields = ("po_number", "supplier", "notes")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "total_amount")
    inlines = [PurchaseOrderItemInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Ensure total amount is recalculated
        obj.total_amount = obj.items.aggregate(total=Sum("total_price"))["total"] or 0
        obj.save()


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ("purchase_order", "item", "quantity", "unit_price", "total_price")
    list_filter = ("purchase_order", "item")
    search_fields = ("item__name", "purchase_order__po_number")
    ordering = ("purchase_order",)
    readonly_fields = ("total_price",)
