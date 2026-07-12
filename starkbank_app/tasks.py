import logging
import random

import starkbank
from celery import shared_task
from django.db import transaction

from starkbank_app.client import StarkBankClient
from starkbank_app.fake import generate_cpf, generate_fullname
from starkbank_app.models import Customer, Invoice

logger = logging.getLogger(__name__)

DESTINATION_ACCOUNT = {
    "bank_code": "20018183",
    "branch_code": "0001",
    "account_number": "6341320293482496",
    "account_type": "payment",
    "name": "Stark Bank S.A.",
    "tax_id": "20.018.183/0001-80",
}


@shared_task
def generate_invoices():
    invoices_count = random.randint(8, 12)
    logger.info(f"generate_invoices: starting, generating {invoices_count} invoices")

    for _ in range(invoices_count):
        with transaction.atomic():
            customer = Customer.objects.create(
                fullname=generate_fullname(), document=generate_cpf()
            )
            Invoice.objects.create(customer=customer, amount=random.randint(100, 10000))

    logger.info(f"generate_invoices: finished, generated {invoices_count} invoices")


def emit_invoice(invoice, user):
    logger.info(f"emit_invoice: starting for invoice {invoice.uuid}")

    invoice_to_process = Invoice.objects.filter(
        pk=invoice.pk, status=Invoice.Status.PENDING
    ).update(status=Invoice.Status.PROCESSING)
    if not invoice_to_process:
        logger.info(
            f"emit_invoice: invoice {invoice.uuid} already claimed by another run, skipping"
        )
        return

    stark_invoice = starkbank.Invoice(
        amount=invoice.amount,
        tax_id=invoice.customer.document,
        name=invoice.customer.fullname,
    )
    created_invoice = starkbank.invoice.create([stark_invoice], user=user)[0]

    invoice.gateway_reference_id = created_invoice.id
    invoice.save(update_fields=["gateway_reference_id"])

    logger.info(
        f"emit_invoice: finished for invoice {invoice.uuid}, gateway_reference_id={invoice.gateway_reference_id}"
    )


@shared_task
def emit_invoices(invoice_ids: list = None):
    user = StarkBankClient.client()
    pending_invoices = Invoice.objects.filter(
        status=Invoice.Status.PENDING
    ).select_related("customer")

    if invoice_ids:
        logger.info(f"emit_invoices: starting for {len(invoice_ids)} selected invoices")
        pending_invoices = pending_invoices.filter(pk__in=invoice_ids)
    else:
        eligible_count = random.randint(8, 12)
        logger.info(
            f"emit_invoices: starting, up to {eligible_count} invoices eligible"
        )
        pending_invoices = pending_invoices.order_by("created_at")[:eligible_count]

    for invoice in pending_invoices:
        emit_invoice(invoice, user)

    logger.info("emit_invoices: finished")


@shared_task
def send_invoice_transfer(gateway_reference_id, amount, fee):
    logger.info(
        f"send_invoice_transfer: starting for invoice gateway_reference_id={gateway_reference_id}"
    )

    paid_invoices = Invoice.objects.filter(
        gateway_reference_id=gateway_reference_id,
        status=Invoice.Status.PAID,
    ).update(status=Invoice.Status.TRANSFERRED)
    if not paid_invoices:
        logger.info(
            f"send_invoice_transfer: invoice {gateway_reference_id} not eligible "
            f"(already transferred or not paid), skipping"
        )
        return

    net_amount = amount - fee
    user = StarkBankClient.client()
    transfer = starkbank.Transfer(
        amount=net_amount,
        external_id=gateway_reference_id,
        **DESTINATION_ACCOUNT,
    )
    created_transfer = starkbank.transfer.create([transfer], user=user)[0]

    Invoice.objects.filter(gateway_reference_id=gateway_reference_id).update(
        gateway_transfer_reference_id=created_transfer.id,
    )

    logger.info(
        f"send_invoice_transfer: finished for invoice {gateway_reference_id}, "
        f"transfer_reference_id={created_transfer.id}, net_amount={net_amount}"
    )
