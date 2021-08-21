import factory
from faker import Faker

fake = Faker(['ru_RU'])
Faker.seed(0)


class CertificateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'movies.Certificate'
        django_get_or_create = ('name',)

    id = factory.Faker('uuid4')
    name = factory.Sequence(lambda _: fake.word())
