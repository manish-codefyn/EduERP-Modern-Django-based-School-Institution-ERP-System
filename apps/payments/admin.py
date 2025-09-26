# payments/admin.py
from django.contrib import admin
from django.utils.html import format_html, format_html_join
import json

from .models import PaymentGateway, OnlinePayment, PaymentWebhookLog, Refund


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = ("gateway_name", "institution", "is_active", "test_mode", "created_at")
    list_filter = ("gateway_name", "institution", "is_active", "test_mode")
    search_fields = ("gateway_name", "institution__name", "merchant_id")
    ordering = ("gateway_name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(OnlinePayment)
class OnlinePaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "payment", "institution", "gateway", "amount", "currency", "status", "created_at")
    list_filter = ("gateway", "status", "currency", "institution")
    search_fields = ("payment__payment_number", "gateway_payment_id", "gateway_order_id")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("institution", "payment", "gateway", "amount", "currency", "status")
        }),
        ("Gateway Info", {
            "fields": ("gateway_payment_id", "gateway_order_id", "gateway_signature", "gateway_response")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )


@admin.register(PaymentWebhookLog)
class PaymentWebhookLogAdmin(admin.ModelAdmin):
    list_display = ("event_type", "gateway", "institution", "processed", "created_at")
    list_filter = ("gateway", "institution", "processed", "event_type")
    search_fields = ("webhook_id", "event_type", "gateway__gateway_name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    def pretty_payload(self, obj):
        return format_html("<pre>{}</pre>", json.dumps(obj.payload, indent=2))
    pretty_payload.short_description = "Payload"

    def pretty_headers(self, obj):
        return format_html("<pre>{}</pre>", json.dumps(obj.headers, indent=2))
    pretty_headers.short_description = "Headers"

    fields = ("institution", "gateway", "webhook_id", "event_type", "signature",
              "processed", "processing_notes", "pretty_payload", "pretty_headers", "created_at")


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("id", "online_payment", "institution", "refund_amount", "status", "created_by", "created_at")
    list_filter = ("status", "institution", "created_by")
    search_fields = ("online_payment__gateway_payment_id", "gateway_refund_id")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("institution", "online_payment", "refund_amount", "reason", "status")
        }),
        ("Gateway", {
            "fields": ("gateway_refund_id", "gateway_response")
        }),
        ("Audit", {
            "fields": ("created_by", "created_at", "updated_at")
        }),
    )
