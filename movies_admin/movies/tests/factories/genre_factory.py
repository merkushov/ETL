import factory
from faker import Faker

fake = Faker(['ru_RU'])
Faker.seed(0)

GENRE_LIST = [
    'Аниме',
    'Биографический',
    'Боевик',
    'Вестерн',
    'Военный',
    'Детектив',
    'Детский',
    'Документальный',
    'Драма',
    'Исторический',
    'Кинокомикс',
    'Комедия',
    'Концерт',
    'Короткометражный',
    'Криминал',
    'Мелодрама',
    'Мистика',
    'Музыка',
    'Мультфильм',
    'Мюзикл',
    'Научный',
    'Нуар',
    'Приключения',
    'Реалити-шоу',
    'Семейный',
    'Спорт',
    'Ток-шоу',
    'Триллер',
    'Ужасы',
    'Фантастика',
    'Фэнтези',
    'Эротика',
]


class GenreFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'movies.Genre'
        django_get_or_create = ('name',)

    id = factory.Faker('uuid4')
    name = factory.Sequence(
        lambda _: '{} {}'.format(
            fake.word(ext_word_list=GENRE_LIST),
            fake.unique.random_int(min=1, max=1000000)
        )
    )
