import factory
from faker import Faker

fake = Faker(['ru_RU'])
Faker.seed(0)


class MovieTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'movies.MovieType'
        django_get_or_create = ('name',)

    id = factory.Faker('uuid4')
    name = factory.Sequence(
        lambda _: fake.word(ext_word_list=['фильм', 'сериал'])
    )
