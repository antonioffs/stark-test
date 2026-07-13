from django.core.exceptions import ValidationError
from faker import Faker
from validate_docbr import CPF

_fake = Faker("pt_BR")
_cpf = CPF()


def generate_cpf():
    return _cpf.generate()


def is_valid_cpf(document):
    return _cpf.validate(document)


def validate_cpf(document):
    if not is_valid_cpf(document):
        raise ValidationError(f"{document} is not a valid CPF.")


def generate_fullname():
    return _fake.name()
