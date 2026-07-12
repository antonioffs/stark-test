from django.contrib import admin

from starkbank_app.models import Customer, Invoice, WebhookInvoiceEvent
from starkbank_app.tasks import emit_invoices


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'fullname', 'document')
    search_fields = ('uuid', 'fullname', 'document')


@admin.action(description='Emit selected invoices')
def trigger_invoice_emission(modeladmin, request, queryset):
    invoice_ids = list(queryset.values_list('pk', flat=True))
    emit_invoices.delay(invoice_ids)
    modeladmin.message_user(request, 'Emit selected invoices runnin in background.')

@admin.action(description='Emit all pending invoices')
def trigger_pending_invoice_emission(modeladmin, request, queryset):
    emit_invoices.delay()
    modeladmin.message_user(request, 'Emit pending invoices running in background.')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'customer', 'gateway_reference_id', 'amount_display', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('gateway_reference_id', 'customer__uuid', 'customer__fullname', 'customer__document')
    actions = [trigger_invoice_emission, trigger_pending_invoice_emission]


@admin.register(WebhookInvoiceEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ('event_id', 'invoice_gateway_reference_id', 'invoice_uuid', 'received_at')
    list_select_related = ('invoice', 'invoice__customer')
    search_fields = ('event_id', 'invoice__uuid', 'invoice__customer__fullname', 'invoice__customer__document')
    readonly_fields = ('event_id', 'invoice', 'received_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def invoice_gateway_reference_id(self, obj):
        return obj.invoice.gateway_reference_id if obj.invoice else None
    invoice_gateway_reference_id.short_description = 'Gateway reference'

    def invoice_uuid(self, obj):
        return obj.invoice.uuid if obj.invoice else None
    invoice_uuid.short_description = 'Invoice UUID'