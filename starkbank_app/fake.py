from faker import Faker
from validate_docbr import CPF

_fake = Faker("pt_BR")
_cpf = CPF()


def generate_cpf():
    return _cpf.generate()


def is_valid_cpf(document):
    return _cpf.validate(document)


def generate_fullname():
    return _fake.name()
