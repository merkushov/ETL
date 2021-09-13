import logging
import json
import dataclasses
from dataclasses import dataclass, field


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, object):
        if dataclasses.is_dataclass(object):
            return dataclasses.asdict(object)
        return super().default(object)


@dataclass(frozen=True)
class Person:
    __slots__ = ("id", "name")
    id: str
    name: str

    @classmethod
    def _get_unique(cls, persons: list["Person"]) -> list["Person"]:
        uniq = {}
        for person in persons:
            uniq.setdefault(person.id, person)

        return list(uniq.values())


@dataclass(frozen=True)
class Actor(Person):
    pass


@dataclass(frozen=True)
class Director(Person):
    pass


@dataclass(frozen=True)
class Writer(Person):
    pass


@dataclass(frozen=False)
class ElasticSearchMovie:
    id: str
    title: str
    type: str
    modified: str
    description: str = field(default='')
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
            modified=db_rows[0]['modified'].strftime("%Y-%m-%d %H:%M:%S.%f"),
        )

        person_classes_map = {
            'актёр': Actor,
            'директор': Director,
            'режисёр': Director,
            'сценарист': Writer,
        }
        persons_map = {
            'Actor': movie.actors,
            'Director': movie.directors,
            'Writer': movie.writers,
        }

        for row in db_rows:
            person_class = person_classes_map.get(row["person_role"], None)
            if not person_class:
                logging.error("Can't handle role type '%s'", row["person_role"])
                next

            person = person_class(
                id=row["person_id"],
                name=row["person_full_name"]
            )
            
            persons_container = persons_map.get(person.__class__.__name__, None)
            if isinstance(persons_container, list):
                persons_container.append(person)

            movie.genres.append(row["genre"])

        # убираем дубли у всех сущностей        
        movie.actors = Actor._get_unique(movie.actors)
        movie.directors = Director._get_unique(movie.directors)
        movie.writers = Writer._get_unique(movie.writers)

        movie.genres = list(set(movie.genres))

        # добавляем списки имён актёров, режисёров, сценаристов
        movie.actors_names = list(map(lambda item: item.name, movie.actors))
        movie.directors_names = list(map(lambda item: item.name, movie.directors))
        movie.writers_names = list(map(lambda item: item.name, movie.writers))

        return movie