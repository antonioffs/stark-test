from uuid import uuid4

from django.db import models


class Customer(models.Model):
    uuid = models.UUIDField(default=uuid4, editable=False, unique=True)
    fullname = models.CharField(max_length=200)
    document = models.CharField(max_length=14)

    def __str__(self):
        return self.fullname


class Invoice(models.Model):

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        PAID = 'paid', 'Paid'
        REFUSED = 'refused', 'Refused'

    uuid = models.UUIDField(default=uuid4, editable=False, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices')
    gateway_reference_id = models.CharField(max_length=50, unique=True)
    amount = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.uuid} - {self.gateway_reference_id} ({self.status})'
