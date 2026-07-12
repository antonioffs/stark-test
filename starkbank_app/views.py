import logging

from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import starkbank
from starkbank.error import InvalidSignatureError

from starkbank_app.client import StarkBankClient
from starkbank_app.models import WebhookInvoiceEvent, Invoice


logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def invoice_process_webhook(request):
    signature = request.headers.get('Digital-Signature', '')

    try:
        event = starkbank.event.parse(
            content=request.body.decode('utf-8'),
            signature=signature,
            user=StarkBankClient.client(),
        )
    except InvalidSignatureError:
        logger.warning('starkbank_webhook: rejected event with invalid signature')
        return HttpResponseBadRequest('invalid signature')

    if event.subscription != 'invoice':
        logger.warning(f'starkbank_webhook: received unexpected subscription {event.subscription}')
        return HttpResponse(status=200)

    try:
        WebhookInvoiceEvent.objects.create(event_id=event.id, gateway_reference_id=event.log.invoice.id)
    except IntegrityError:
        logger.info(f'starkbank_webhook: event {event.id} already processed, skipping')
        return HttpResponse(status=200)

    if event.log.type == 'paid':
        Invoice.mark_invoice_as_paid(gateway_reference_id=event.log.invoice.id)

    return HttpResponse(status=200)


