from django.urls import path

from starkbank_app import views

urlpatterns = [
    path('invoice-webhook/starkbank', views.invoice_process_webhook, name='starkbank-invoice-webhook'),
]
