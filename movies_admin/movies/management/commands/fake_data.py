from django.core.management.base import BaseCommand
from movies.tests.factories.genre_factory import GenreFactory
from movies.tests.factories.person_factory import PersonFactory
from movies.tests.factories.person_role_factory import PersonRoleFactory
from movies.tests.factories.movie_type_factory import MovieTypeFactory
from movies.tests.factories.movies_factory import MovieFactory
from movies.models import (
    Genre,
    MoviePersonRole,
    Person,
    Movie,
    MovieGenre,
)
import random

BATCH_SIZE = 10000


class Command(BaseCommand):
    help = 'Generates a large amount of fake data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count_genres',
            type=int,
            default=1000,
            help='The number of elements (Genre) to generate',
        )
        parser.add_argument(
            '--count_persons',
            type=int,
            default=10000,
            help='The number of elements (Person) to generate'
        )
        parser.add_argument(
            '--count_movies',
            type=int,
            default=50000,
            help='The number of elements (Movies) to generate',
        )
        parser.add_argument(
            '--movie_genre_coeff',
            type=int,
            default=3,
            help='Determines how much more the total '
            'number of links of films with genres will be',
        )
        parser.add_argument(
            '--movie_actor_coeff',
            type=int,
            default=15,
            help='Determines how much more the total '
            'number of links of films with actors will be',
        )
        parser.add_argument(
            '--movie_director_coeff',
            type=int,
            default=2,
            help='Determines how much more the total '
            'number of links of films with directors will be',
        )
        parser.add_argument(
            '--movie_writer_coeff',
            type=int,
            default=3,
            help='Determines how much more the total '
            'number of links of films with writers will be',
        )

    def handle(self, *args, **options):
        print("Start processing Person (bulk_create)")
        persons = PersonFactory.build_batch(options['count_persons'])
        Person.objects.bulk_create(persons, batch_size=BATCH_SIZE)
        print("Finish processing Person")

        print("Start processing Genre (bulk_create)")
        genres = GenreFactory.build_batch(options['count_genres'])
        Genre.objects.bulk_create(genres, batch_size=BATCH_SIZE)
        print("Finish processing Genre")

        type_movie = MovieTypeFactory(name='фильм')
        type_show = MovieTypeFactory(name='сериал')

        print("Start processing Movie (bulk_create)")
        movies = MovieFactory.build_batch(options['count_movies'] - int(options['count_movies'] / 4), type=type_movie)
        shows = MovieFactory.build_batch(int(options['count_movies'] / 4), type=type_show)
        Movie.objects.bulk_create(movies, batch_size=BATCH_SIZE)
        Movie.objects.bulk_create(shows, batch_size=BATCH_SIZE)
        print("Finish processing Movie")

        actor = PersonRoleFactory(name='актёр')
        director = PersonRoleFactory(name='директор')
        writer = PersonRoleFactory(name='сценарист')

        movie_genres = []
        movie_persons = []

        print("Start processing MovieGenres and MoviePersons (bulk_create)")
        for movie in [*movies, *shows]:
            for genre in random.choices(genres, k=options["movie_genre_coeff"]):
                movie_genres.append(
                    MovieGenre(
                        movie=movie,
                        genre=genre
                    )
                )

            person_role = []
            person_role += [
                [person, director] for person in random.choices(persons, k=options["movie_director_coeff"])
            ]
            person_role += [
                [person, writer] for person in random.choices(persons, k=options["movie_writer_coeff"])
            ]
            person_role += [
                [person, actor] for person in random.choices(persons, k=options["movie_actor_coeff"])
            ]

            for item in person_role:
                movie_persons.append(
                    MoviePersonRole(movie=movie, person=item[0], person_role=item[1])
                )

        MovieGenre.objects.bulk_create(
            movie_genres,
            batch_size=BATCH_SIZE,
            ignore_conflicts=True
        )
        MoviePersonRole.objects.bulk_create(
            movie_persons,
            batch_size=BATCH_SIZE,
            ignore_conflicts=True
        )
        print("Finish processing MovieGenres and MoviePersons")

        self.stdout.write(self.style.SUCCESS('Success'))
