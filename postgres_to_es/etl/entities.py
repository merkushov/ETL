import dataclasses
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Person:
    __slots__ = ("id", "name")
    id: str
    name: str


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
class Movie:
    imdb_identifier: str
    title: str
    imdb_rating: float = field(default=0.0)
    genres: list = field(default_factory=list)
    description: str = field(default='')
    directors: list[Director] = field(default_factory=list)
    writers: list[Writer] = field(default_factory=list)
    actors: list[Actor] = field(default_factory=list)
