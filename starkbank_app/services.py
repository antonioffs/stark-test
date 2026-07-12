import logging
from django.db import transaction, IntegrityError

from starkbank_app.models import Invoice, WebhookInvoiceEvent
from starkbank_app.tasks import send_invoice_transfer


logger = logging.getLogger(__name__)

def create_webhook_invoice_event(event, payload):
    invoice = Invoice.objects.filter(gateway_reference_id=event.log.invoice.id).first()

    try:
        with transaction.atomic():
            WebhookInvoiceEvent.objects.create(
                event_id=event.id,
                invoice=invoice,
                status=event.log.invoice.status,
                amount=event.log.invoice.amount,
                fee=event.log.invoice.fee,
                interest_percent=event.log.invoice.interest,
                expiration=event.log.invoice.expiration,
                payload=payload,
            )
    except IntegrityError:
        logger.info(f'starkbank_webhook: event {event.id} already processed, skipping')
        return

    if event.log.invoice.status == 'paid':
        Invoice.mark_invoice_as_paid(gateway_reference_id=event.log.invoice.id)
        send_invoice_transfer.delay(
            gateway_reference_id=event.log.invoice.id,
            amount=event.log.invoice.amount,
            fee=event.log.invoice.fee,
        )
    elif event.log.invoice.status == 'overdue':
        Invoice.mark_invoice_as_refused(gateway_reference_id=event.log.invoice.id)
    elif event.log.invoice.status == 'canceled':
        Invoice.mark_invoice_as_cancelled(gateway_reference_id=event.log.invoice.id)