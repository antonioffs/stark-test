import logging
import random

import starkbank
from celery import shared_task
from django.db import transaction

from starkbank_app.client import StarkBankClient
from starkbank_app.fake import generate_cpf, generate_fullname
from starkbank_app.models import Customer, Invoice

logger = logging.getLogger(__name__)


@shared_task
def generate_invoices():
    invoices_count = random.randint(8, 12)
    logger.info(f'generate_invoices: starting, generating {invoices_count} invoices')

    for _ in range(invoices_count):
        with transaction.atomic():
            customer = Customer.objects.create(fullname=generate_fullname(), document=generate_cpf())
            Invoice.objects.create(customer=customer, amount=random.randint(100, 10000))

    logger.info(f'generate_invoices: finished, generated {invoices_count} invoices')


def emit_invoice(invoice, user):
    logger.info(f'emit_invoice: starting for invoice {invoice.uuid}')

    claimed = Invoice.objects.filter(pk=invoice.pk, status=Invoice.Status.PENDING).update(
        status=Invoice.Status.PROCESSING
    )
    if not claimed:
        logger.info(f'emit_invoice: invoice {invoice.uuid} already claimed by another run, skipping')
        return

    stark_invoice = starkbank.Invoice(
        amount=invoice.amount,
        tax_id=invoice.customer.document,
        name=invoice.customer.fullname,
    )
    created_invoice = starkbank.invoice.create([stark_invoice], user=user)[0]

    invoice.gateway_reference_id = created_invoice.id
    invoice.save(update_fields=['gateway_reference_id'])

    logger.info(f'emit_invoice: finished for invoice {invoice.uuid}, gateway_reference_id={invoice.gateway_reference_id}')


@shared_task
def emit_invoices():
    eligible_count = random.randint(8, 12)
    logger.info(f'emit_invoices: starting, up to {eligible_count} invoices eligible')

    user = StarkBankClient.client()
    pending_invoices = (
        Invoice.objects.filter(status=Invoice.Status.PENDING)
        .select_related('customer')
        .order_by('created_at')[:eligible_count]
    )
    for invoice in pending_invoices:
        emit_invoice(invoice, user)

    logger.info('emit_invoices: finished')