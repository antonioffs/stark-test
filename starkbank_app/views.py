import logging

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import starkbank
from starkbank.error import InvalidSignatureError

from starkbank_app.client import StarkBankClient
from starkbank_app.services import create_webhook_invoice_event

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def invoice_process_webhook(request):
    signature = request.headers.get("Digital-Signature", "")
    payload = request.body.decode("utf-8")

    try:
        event = starkbank.event.parse(
            content=payload,
            signature=signature,
            user=StarkBankClient.client(),
        )
    except InvalidSignatureError:
        logger.warning("starkbank_webhook: rejected event with invalid signature")
        return HttpResponseBadRequest("invalid signature")

    if event.subscription != "invoice":
        logger.warning(
            f"starkbank_webhook: received unexpected subscription {event.subscription}"
        )
        return HttpResponse(status=200)

    create_webhook_invoice_event(event, payload)
    return HttpResponse(status=200)
