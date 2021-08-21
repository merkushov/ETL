import factory
from faker import Faker

fake = Faker(['ru_RU'])
Faker.seed(0)


class PersonRoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'movies.PersonRole'
        django_get_or_create = ('name',)

    id = factory.Faker('uuid4')
    name = factory.Sequence(
        lambda _: fake.word(ext_word_list=['актёр', 'режисёр', 'сценарист'])
    )
    description = factory.Sequence(lambda _: fake.text(max_nb_chars=100))
