import logging
from django.db import transaction, IntegrityError

from starkbank_app.models import Invoice, WebhookInvoiceEvent


logger = logging.getLogger(__name__)

def create_webhook_invoice_event(event):

    invoice = Invoice.objects.filter(gateway_reference_id=event.log.invoice.id).first()

    try:
        with transaction.atomic():
            WebhookInvoiceEvent.objects.create(event_id=event.id, invoice=invoice)
    except IntegrityError:
        logger.info(f'starkbank_webhook: event {event.id} already processed, skipping')
        return

    if event.log.type == 'paid':
        Invoice.mark_invoice_as_paid(gateway_reference_id=event.log.invoice.id)
