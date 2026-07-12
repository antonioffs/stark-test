from datetime import timedelta
from itertools import count
from unittest.mock import patch

import pytest
import starkbank
from django.utils import timezone
from starkbank.error import InvalidSignatureError

from starkbank_app.client import StarkBankClient
from starkbank_app.fake import generate_cpf, generate_fullname, is_valid_cpf
from starkbank_app.models import Customer, Invoice, WebhookInvoiceEvent
from starkbank_app.tasks import emit_invoice, emit_invoices, generate_invoices



class FakeInvoiceLog:
    def __init__(self, event_type, invoice_gateway_id, amount=1000, fee=50, interest=10, expiration=timedelta(days=2)):
        self.type = event_type
        self.invoice = type('FakeInvoice', (), {
            'id': invoice_gateway_id,
            'status': event_type,
            'amount': amount,
            'fee': fee,
            'interest': interest,
            'expiration': expiration,
        })()


class FakeEvent:
    def __init__(self, event_id, subscription, log):
        self.id = event_id
        self.subscription = subscription
        self.log = log


def test_generate_cpf_returns_a_valid_cpf():
    assert is_valid_cpf(generate_cpf())


def test_is_valid_cpf_rejects_repeated_digits():
    assert not is_valid_cpf('111.111.111-11')


def test_is_valid_cpf_rejects_wrong_length():
    assert not is_valid_cpf('123')


def test_generate_fullname_returns_a_non_empty_string():
    fullname = generate_fullname()

    assert isinstance(fullname, str)
    assert fullname.strip() != ''


@pytest.mark.django_db
def test_communicates_with_starkbank_and_retrieves_balance():
    balance = starkbank.balance.get(user=StarkBankClient.client())

    assert balance.id is not None


class FakeCreatedInvoice:

    def __init__(self, gateway_id):
        self.id = gateway_id
        self.status = 'created'


_gateway_id_sequence = count()


def fake_starkbank_create(invoices, user=None):
    return [FakeCreatedInvoice(f'gateway-id-{next(_gateway_id_sequence)}') for _ in invoices]


def _create_pending_invoice():
    customer = Customer.objects.create(fullname='Fulano de Tal', document='12345678901')
    return Invoice.objects.create(customer=customer, amount=1000)


@pytest.mark.django_db
def test_generate_invoices_creates_between_8_and_12_pending_invoices():
    generate_invoices()

    invoices = Invoice.objects.all()
    assert 8 <= invoices.count() <= 12
    assert Customer.objects.count() == invoices.count()

    for invoice in invoices:
        assert invoice.status == Invoice.Status.PENDING
        assert invoice.gateway_reference_id is None
        assert 100 <= invoice.amount <= 10000


@pytest.mark.django_db
@patch('starkbank_app.tasks.starkbank.invoice.create', side_effect=fake_starkbank_create)
def test_emit_invoices_emits_only_pending_invoices_and_moves_them_to_processing(mock_create):
    for _ in range(15):
        _create_pending_invoice()

    already_paid_customer = Customer.objects.create(fullname='Ciclano', document='98765432100')
    paid_invoice = Invoice.objects.create(
        customer=already_paid_customer,
        amount=500,
        status=Invoice.Status.PAID,
        gateway_reference_id='already-paid',
    )

    emit_invoices()

    processing_invoices = Invoice.objects.filter(status=Invoice.Status.PROCESSING)
    assert 8 <= processing_invoices.count() <= 12
    for invoice in processing_invoices:
        assert invoice.gateway_reference_id is not None

    paid_invoice.refresh_from_db()
    assert paid_invoice.status == Invoice.Status.PAID
    assert paid_invoice.gateway_reference_id == 'already-paid'


@pytest.mark.django_db
@patch('starkbank_app.tasks.starkbank.invoice.create', return_value=[FakeCreatedInvoice('gateway-id-fixed')])
def test_emit_invoice_does_not_re_emit_an_already_processing_invoice(mock_create):
    invoice = _create_pending_invoice()
    user = StarkBankClient.client()

    emit_invoice(invoice, user)
    emit_invoice(Invoice.objects.get(pk=invoice.pk), user)

    assert mock_create.call_count == 1
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PROCESSING
    assert invoice.gateway_reference_id == 'gateway-id-fixed'


@pytest.mark.django_db
@patch('starkbank_app.tasks.starkbank.invoice.create', side_effect=fake_starkbank_create)
def test_emit_invoices_with_ids_emits_all_selected_invoices_ignoring_the_random_cap(mock_create):
    selected = [_create_pending_invoice() for _ in range(15)]
    not_selected = _create_pending_invoice()

    emit_invoices(invoice_ids=[invoice.pk for invoice in selected])

    assert mock_create.call_count == 15
    for invoice in selected:
        invoice.refresh_from_db()
        assert invoice.status == Invoice.Status.PROCESSING
        assert invoice.gateway_reference_id is not None

    not_selected.refresh_from_db()
    assert not_selected.status == Invoice.Status.PENDING
    assert not_selected.gateway_reference_id is None

@pytest.mark.django_db
@patch('starkbank_app.views.starkbank.event.parse')
def test_webhook_rejects_invalid_signature(mock_parse, client):
    mock_parse.side_effect = InvalidSignatureError('bad signature')

    response = client.post(
        '/invoice-webhook/starkbank', data='{}', content_type='application/json',
        HTTP_DIGITAL_SIGNATURE='invalid',
    )

    assert response.status_code == 400
    assert WebhookInvoiceEvent.objects.count() == 0


@pytest.mark.django_db
@patch('starkbank_app.views.starkbank.event.parse')
def test_webhook_ignores_unexpected_subscription(mock_parse, client):
    mock_parse.return_value = FakeEvent(
        event_id='event-1', subscription='transfer', log=FakeInvoiceLog('paid', 'irrelevant'),
    )

    response = client.post(
        '/invoice-webhook/starkbank', data='{}', content_type='application/json',
        HTTP_DIGITAL_SIGNATURE='valid',
    )

    assert response.status_code == 200
    assert WebhookInvoiceEvent.objects.count() == 0


@pytest.mark.django_db
@patch('starkbank_app.views.starkbank.event.parse')
def test_webhook_marks_invoice_as_paid_on_paid_event(mock_parse, client):
    invoice = _create_pending_invoice()
    invoice.gateway_reference_id = 'gateway-id-fixed'
    invoice.status = Invoice.Status.PROCESSING
    invoice.save()

    mock_parse.return_value = FakeEvent(
        event_id='event-1', subscription='invoice', log=FakeInvoiceLog('paid', 'gateway-id-fixed'),
    )

    response = client.post(
        '/invoice-webhook/starkbank', data='{}', content_type='application/json',
        HTTP_DIGITAL_SIGNATURE='valid',
    )

    assert response.status_code == 200
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID

    event = WebhookInvoiceEvent.objects.get(event_id='event-1')
    assert event.invoice_id == invoice.id


@pytest.mark.django_db
@patch('starkbank_app.views.starkbank.event.parse')
def test_webhook_marks_invoice_as_refused_on_overdue_event(mock_parse, client):
    invoice = _create_pending_invoice()
    invoice.gateway_reference_id = 'gateway-id-fixed'
    invoice.status = Invoice.Status.PROCESSING
    invoice.save()

    mock_parse.return_value = FakeEvent(
        event_id='event-1', subscription='invoice', log=FakeInvoiceLog('overdue', 'gateway-id-fixed'),
    )

    response = client.post(
        '/invoice-webhook/starkbank', data='{}', content_type='application/json',
        HTTP_DIGITAL_SIGNATURE='valid',
    )

    assert response.status_code == 200
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.REFUSED

    event = WebhookInvoiceEvent.objects.get(event_id='event-1')
    assert event.status == 'overdue'


@pytest.mark.django_db
@patch('starkbank_app.views.starkbank.event.parse')
def test_webhook_marks_invoice_as_canceled_on_canceled_event(mock_parse, client):
    invoice = _create_pending_invoice()
    invoice.gateway_reference_id = 'gateway-id-fixed'
    invoice.status = Invoice.Status.PROCESSING
    invoice.save()

    mock_parse.return_value = FakeEvent(
        event_id='event-1', subscription='invoice', log=FakeInvoiceLog('canceled', 'gateway-id-fixed'),
    )

    response = client.post(
        '/invoice-webhook/starkbank', data='{}', content_type='application/json',
        HTTP_DIGITAL_SIGNATURE='valid',
    )

    assert response.status_code == 200
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.CANCELED

    event = WebhookInvoiceEvent.objects.get(event_id='event-1')
    assert event.status == 'canceled'


@pytest.mark.django_db
@patch('starkbank_app.views.starkbank.event.parse')
def test_webhook_does_not_change_status_for_non_paid_event(mock_parse, client):
    invoice = _create_pending_invoice()
    invoice.gateway_reference_id = 'gateway-id-fixed'
    invoice.save()

    mock_parse.return_value = FakeEvent(
        event_id='event-1', subscription='invoice', log=FakeInvoiceLog('registered', 'gateway-id-fixed'),
    )

    response = client.post(
        '/invoice-webhook/starkbank', data='{}', content_type='application/json',
        HTTP_DIGITAL_SIGNATURE='valid',
    )

    assert response.status_code == 200
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PENDING
    assert WebhookInvoiceEvent.objects.filter(event_id='event-1').exists()


@pytest.mark.django_db
@patch('starkbank_app.views.starkbank.event.parse')
def test_webhook_does_not_reprocess_redelivered_event(mock_parse, client):
    invoice = _create_pending_invoice()
    invoice.gateway_reference_id = 'gateway-id-fixed'
    invoice.save()
    WebhookInvoiceEvent.objects.create(
        event_id='event-1', invoice=invoice, status='paid', amount=1000, fee=50, interest_percent=10,
        expiration=timedelta(days=2), payload='{}',
    )

    mock_parse.return_value = FakeEvent(
        event_id='event-1', subscription='invoice', log=FakeInvoiceLog('paid', 'gateway-id-fixed'),
    )

    response = client.post(
        '/invoice-webhook/starkbank', data='{}', content_type='application/json',
        HTTP_DIGITAL_SIGNATURE='valid',
    )

    assert response.status_code == 200
    invoice.refresh_from_db()
    assert invoice.status != Invoice.Status.PAID  # não reprocessado


@pytest.mark.django_db
@patch('starkbank_app.views.starkbank.event.parse')
def test_webhook_records_event_without_matching_local_invoice(mock_parse, client):
    mock_parse.return_value = FakeEvent(
        event_id='event-1', subscription='invoice', log=FakeInvoiceLog('paid', 'unknown-gateway-id'),
    )

    response = client.post(
        '/invoice-webhook/starkbank', data='{}', content_type='application/json',
        HTTP_DIGITAL_SIGNATURE='valid',
    )

    assert response.status_code == 200
    event = WebhookInvoiceEvent.objects.get(event_id='event-1')
    assert event.invoice is None
