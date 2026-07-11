import starkbank
from django.test import TestCase

from starkbank_app.client import StarkBankClient


class StarkBankClientTest(TestCase):

    def test_communicates_with_starkbank_and_retrieves_balance(self):
        balance = starkbank.balance.get(user=StarkBankClient.client())

        self.assertIsNotNone(balance.id)
