from django.contrib import admin

from starkbank_app.models import Customer, Invoice
from starkbank_app.tasks import emit_invoices


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'fullname', 'document')
    search_fields = ('fullname', 'document')


@admin.action(description='Disparar emissão de novas invoices')
def trigger_invoice_emission(modeladmin, request, queryset):
    emit_invoices.delay()
    modeladmin.message_user(request, 'Emissão de invoices disparada em background.')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'customer', 'gateway_reference_id', 'amount_display', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('gateway_reference_id', 'customer__fullname', 'customer__document')
    actions = [trigger_invoice_emission]
