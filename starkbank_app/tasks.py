import random

import starkbank
from celery import shared_task
from django.db import transaction

from starkbank_app.client import StarkBankClient
from starkbank_app.fake import generate_cpf, generate_fullname
from starkbank_app.models import Customer, Invoice


@shared_task
def generate_invoices():
    people_count = random.randint(8, 12)

    for _ in range(people_count):
        with transaction.atomic():
            customer = Customer.objects.create(fullname=generate_fullname(), document=generate_cpf())
            Invoice.objects.create(customer=customer, amount=random.randint(100, 10000))


def emit_invoice(invoice):
    claimed = Invoice.objects.filter(pk=invoice.pk, status=Invoice.Status.PENDING).update(
        status=Invoice.Status.PROCESSING
    )
    if not claimed:
        return

    stark_invoice = starkbank.Invoice(
        amount=invoice.amount,
        tax_id=invoice.customer.document,
        name=invoice.customer.fullname,
    )
    created_invoice = starkbank.invoice.create([stark_invoice], user=StarkBankClient.client())[0]

    invoice.gateway_reference_id = created_invoice.id
    invoice.save(update_fields=['gateway_reference_id'])


@shared_task
def emit_invoices():
    eligible_count = random.randint(8, 12)
    pending_invoices = Invoice.objects.filter(status=Invoice.Status.PENDING)[:eligible_count]

    for invoice in pending_invoices:
        emit_invoice(invoice)