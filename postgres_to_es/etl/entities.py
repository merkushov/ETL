import dataclasses
import json
import logging
from dataclasses import dataclass, field


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, object):
        if dataclasses.is_dataclass(object):
            return dataclasses.asdict(object)
        return super().default(object)


@dataclass(frozen=True)
class BasicStructure:
    __slots__ = ("id", "name")
    id: str
    name: str

    @classmethod
    def _get_unique_by_id(
        cls, structure: list["BasicStructure"]
    ) -> list["BasicStructure"]:
        uniq = {}
        for item in structure:
            uniq.setdefault(item.id, item)

        return list(uniq.values())


@dataclass(frozen=True)
class Person(BasicStructure):
    pass


@dataclass(frozen=True)
class Actor(Person):
    pass


@dataclass(frozen=True)
class Director(Person):
    pass


@dataclass(frozen=True)
class Writer(Person):
    pass


@dataclass(frozen=True)
class Genre(BasicStructure):
    pass


@dataclass(frozen=False)
class ElasticSearchMovie:
    id: str
    title: str
    type: str
    modified: str
    description: str = field(default="")
    imdb_rating: float = field(default=0.0)
    genres: list = field(default_factory=list)
    actors: list[Actor] = field(default_factory=list)
    directors: list[Director] = field(default_factory=list)
    writers: list[Writer] = field(default_factory=list)
    actors_names: list = field(default_factory=list)
    directors_names: list = field(default_factory=list)
    writers_names: list = field(default_factory=list)

    @classmethod
    def init_by_db_rows(cls, db_rows: list) -> "ElasticSearchMovie":
        """
        Инициализирует объект данными из БД
        Данные из БД это строки таблиц фильмов и связанных сущностей,
        сджойненные вмесет. Содержат много дублированной информации.
        На вход должны приходить списки с одинаковым movie_id
        """
        movie = ElasticSearchMovie(
            id=db_rows[0]["movie_id"],
            title=db_rows[0]["title"],
            description=db_rows[0]["description"],
            imdb_rating=db_rows[0]["rating"],
            type=db_rows[0]["type"],
            modified=db_rows[0]["modified"].strftime("%Y-%m-%d %H:%M:%S.%f"),
        )

        person_classes_map = {
            "актёр": Actor,
            "директор": Director,
            "режисёр": Director,
            "сценарист": Writer,
        }
        persons_map = {
            "Actor": movie.actors,
            "Director": movie.directors,
            "Writer": movie.writers,
        }

        for row in db_rows:
            person_class = person_classes_map.get(row["person_role"], None)
            if not person_class:
                logging.error("Can't handle role type '%s'", row["person_role"])
                next

            person = person_class(id=row["person_id"], name=row["person_full_name"])

            persons_container = persons_map.get(person.__class__.__name__, None)
            if isinstance(persons_container, list):
                persons_container.append(person)

            movie.genres.append(Genre(id=row["genre_id"], name=row["genre_name"]))

        # убираем дубли у всех сущностей
        movie.actors = Actor._get_unique_by_id(movie.actors)
        movie.directors = Director._get_unique_by_id(movie.directors)
        movie.writers = Writer._get_unique_by_id(movie.writers)

        movie.genres = Genre._get_unique_by_id(movie.genres)

        # добавляем списки имён актёров, режисёров, сценаристов
        movie.actors_names = list(map(lambda item: item.name, movie.actors))
        movie.directors_names = list(map(lambda item: item.name, movie.directors))
        movie.writers_names = list(map(lambda item: item.name, movie.writers))

        return movie


@dataclass(frozen=True)
class MovieSmallWithIMDBRating:
    id: str
    title: str
    imdb_rating: float


@dataclass(frozen=False)
class ElasticSearchGenre:
    id: str
    name: str
    modified: str
    movies: list[MovieSmallWithIMDBRating] = field(default_factory=list)

    @classmethod
    def init_by_db_rows(cls, db_rows: list) -> "ElasticSearchMovie":
        """
        Инициализирует объект данными из БД
        Данные из БД это строки таблиц жанров и связанных сущностей (фильмов),
        сджойненные вмесет. Содержат много дублированной информации.
        На вход должны приходить списки с одинаковым genre_id
        """
        genre = ElasticSearchGenre(
            id=db_rows[0]["genre_id"],
            name=db_rows[0]["genre_name"],
            modified=db_rows[0]["modified"].strftime("%Y-%m-%d %H:%M:%S.%f"),
        )

        for row in db_rows:
            genre.movies.append(
                MovieSmallWithIMDBRating(
                    id=row["movie_id"],
                    title=row["movie_title"],
                    imdb_rating=row["movie_rating"],
                )
            )

        return genre


@dataclass(frozen=True)
class MovieSmallWithPersonRole:
    id: str
    title: str
    person_role: str

    # TODO: вынести _get_unique_by_id отдельным методом. Отрефакторить тут
    #       и в BasicStructure
    @classmethod
    def _get_unique_by_id(
        cls, structure: list["MovieSmallWithPersonRole"]
    ) -> list["MovieSmallWithPersonRole"]:
        uniq = {}
        for item in structure:
            uniq.setdefault(item.id, item)

        return list(uniq.values())


@dataclass(frozen=False)
class ElasticSearchPerson:
    id: str
    full_name: str
    modified: str
    movies: list[MovieSmallWithPersonRole] = field(default_factory=list)

    @classmethod
    def init_by_db_rows(cls, db_rows: list) -> "ElasticSearchMovie":
        """
        Инициализирует объект данными из БД
        Данные из БД это строки таблиц Персон и связанных сущностей (фильмов),
        сджойненные вмесет. Содержат много дублированной информации.
        На вход должны приходить списки с одинаковым person_id
        """
        obj = ElasticSearchPerson(
            id=db_rows[0]["person_id"],
            full_name=db_rows[0]["person_full_name"],
            modified=db_rows[0]["modified"].strftime("%Y-%m-%d %H:%M:%S.%f"),
        )

        person_map = {
            "актёр": "actor",
            "директор": "director",
            "режисёр": "director",
            "сценарист": "writer",
        }

        for row in db_rows:
            obj.movies.append(
                MovieSmallWithPersonRole(
                    id=row["movie_id"],
                    title=row["movie_title"],
                    person_role=person_map.get(row["person_role_name"], None),
                )
            )

        obj.movies = MovieSmallWithPersonRole._get_unique_by_id(obj.movies)

        return obj
