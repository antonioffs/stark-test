import logging
from uuid import uuid4

from django.db import models

logger = logging.getLogger(__name__)


class Customer(models.Model):
    uuid = models.UUIDField(default=uuid4, editable=False, unique=True)
    fullname = models.CharField(max_length=200)
    document = models.CharField(max_length=11)

    def __str__(self):
        return self.fullname


class Invoice(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        PAID = "paid", "Paid"
        TRANSFERRED = "transferred", "Transferred"
        CANCELED = "canceled", "Canceled"
        REFUSED = "refused", "Refused"

    uuid = models.UUIDField(default=uuid4, editable=False, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="invoices"
    )
    gateway_reference_id = models.CharField(
        max_length=50, unique=True, null=True, blank=True
    )
    gateway_transfer_reference_id = models.CharField(
        max_length=50, unique=True, null=True, blank=True
    )
    amount = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.uuid} - {self.gateway_reference_id} ({self.status})"

    def amount_display(self):
        return (
            f"R$ {self.amount / 100:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    amount_display.short_description = "Amount"

    @staticmethod
    def _update_invoice_status(gateway_reference_id, status):
        updated = (
            Invoice.objects.filter(
                gateway_reference_id=gateway_reference_id,
            )
            .exclude(status=status)
            .update(status=status)
        )
        if updated:
            logger.info(
                f"starkbank_webhook: invoice {gateway_reference_id} updated to {status}"
            )
        else:
            logger.warning(
                f"starkbank_webhook: no local invoice found for gateway_reference_id={gateway_reference_id}"
            )

    @staticmethod
    def mark_invoice_as_paid(gateway_reference_id):
        Invoice._update_invoice_status(gateway_reference_id, Invoice.Status.PAID)

    @staticmethod
    def mark_invoice_as_refused(gateway_reference_id):
        Invoice._update_invoice_status(gateway_reference_id, Invoice.Status.REFUSED)

    @staticmethod
    def mark_invoice_as_cancelled(gateway_reference_id):
        Invoice._update_invoice_status(gateway_reference_id, Invoice.Status.CANCELED)


class WebhookInvoiceEvent(models.Model):
    event_id = models.CharField(max_length=50, unique=True)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="webhook_events",
    )
    status = models.CharField(max_length=20, null=True)
    received_at = models.DateTimeField(auto_now_add=True)
    amount = models.PositiveIntegerField(null=True)
    fee = models.PositiveIntegerField(null=True)
    interest_percent = models.PositiveIntegerField(null=True)
    expiration = models.DurationField(null=True)
    payload = models.TextField(null=True)

    def __str__(self):
        return self.event_id
