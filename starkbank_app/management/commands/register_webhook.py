import logging
import time
from urllib.parse import urlparse

import requests
import starkbank
from django.core.management.base import BaseCommand
from starkcore.error import InputErrors

from starkbank_app.client import StarkBankClient

logger = logging.getLogger(__name__)

NGROK_API_URL = 'http://ngrok:4040/api/tunnels'
WEBHOOK_PATH = '/invoice-webhook/starkbank'
NGROK_HOST_SUFFIXES = ('.ngrok-free.app', '.ngrok-free.dev', '.ngrok.app', '.ngrok.io')

class Command(BaseCommand):
    help = 'Discovers the current ngrok public URL and registers it as the Stark Bank invoice Webhook.'

    def handle(self, *args, **options):
        public_url = self._wait_for_ngrok_url()
        user = StarkBankClient.client()
        target_url = f'{public_url}{WEBHOOK_PATH}'

        existing_ngrok_webhooks = self._find_ngrok_webhooks(user)
        if any(webhook.url == target_url for webhook in existing_ngrok_webhooks):
            logger.info(f'register_webhook: {target_url} already registered, skipping')
            return

        for webhook in existing_ngrok_webhooks:
            starkbank.webhook.delete(webhook.id, user=user)
            logger.info(f'register_webhook: removed stale webhook {webhook.id} -> {webhook.url}')

        try:
            webhook = starkbank.webhook.create(
                url=target_url,
                subscriptions=['invoice'],
                user=user,
            )
            logger.info(f'register_webhook: registered webhook {webhook.id} -> {webhook.url}')
        except InputErrors as error:
            if any(err.code == 'invalidUrl' for err in error.errors):
                # Stark Bank's webhook.query() can lag behind webhook.create()'s own
                # uniqueness check, so a delete we just issued may not be visible yet.
                # The desired end state (this URL registered for 'invoice') already
                # holds, so treat the conflict as success instead of retrying/failing.
                logger.info(f'register_webhook: {target_url} already registered, skipping')
            else:
                raise

    def _wait_for_ngrok_url(self, attempts=15, delay=2):
        for _ in range(attempts):
            try:
                response = requests.get(NGROK_API_URL, timeout=5)
                for tunnel in response.json().get('tunnels', []):
                    if tunnel['public_url'].startswith('https://'):
                        return tunnel['public_url']
            except requests.exceptions.RequestException:
                pass
            time.sleep(delay)
        raise RuntimeError('register_webhook: ngrok tunnel did not become available in time')

    def _find_ngrok_webhooks(self, user):
        return [
            webhook for webhook in starkbank.webhook.query(user=user)
            if (urlparse(webhook.url).hostname or '').endswith(NGROK_HOST_SUFFIXES)
        ]