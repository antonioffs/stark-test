import starkbank
from django.conf import settings


class StarkBankClient:

    def project(self):
        return starkbank.Project(
            environment=settings.STARKBANK_ENVIRONMENT,
            id=settings.STARKBANK_PROJECT_ID,
            private_key=settings.STARKBANK_KEY,
        )
