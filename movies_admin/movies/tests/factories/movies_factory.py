import factory
from faker import Faker
from movies.tests.factories.movie_type_factory import MovieTypeFactory

fake = Faker(['ru_RU'])
Faker.seed(0)


class MovieFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'movies.Movie'

    id = factory.Faker('uuid4')
    title = factory.Sequence(lambda _: fake.text(max_nb_chars=50))
    description = factory.Sequence(lambda _: fake.text(max_nb_chars=500))
    imdb_identifier = factory.Sequence(
        lambda _: 'tt{}'.format(
            fake.unique.random_int(min=10000000, max=100000000)
        )
    )
    creation_date = factory.Sequence(lambda _: fake.date())
    file_path = factory.Sequence(
        lambda _: fake.file_path(depth=5, category='video')
    )
    rating = factory.Sequence(
        lambda _: fake.pyfloat(right_digits=1, min_value=0, max_value=10)
    )
    type = factory.SubFactory(MovieTypeFactory)
