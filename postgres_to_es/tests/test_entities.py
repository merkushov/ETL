import logging
from datetime import datetime

import pytest
from etl.entities import ElasticSearchMovie, Person

logger = logging.getLogger()

db_rows_movies = [
    {
        "movie_id": "test1",
        "title": "test",
        "description": "description",
        "rating": 7.7,
        "type": "movie",
        "modified": datetime.now(),
    }
]
db_rows_actors = [
    {
        "person_role": "актёр",
        "person_id": "person_test_1",
        "person_full_name": "Иванов Иван Иванович",
    },
    {
        "person_role": "актёр",
        "person_id": "person_test_2",
        "person_full_name": "Петров Пётр Петрович",
    },
]
db_rows_directors = [
    {
        "person_role": "режисёр",
        "person_id": "person_test_10",
        "person_full_name": "Иванов Артём Артёмович",
    },
    {
        "person_role": "режисёр",
        "person_id": "person_test_11",
        "person_full_name": "Петров Игорь Игоревич",
    },
]
db_rows_writers = [
    {
        "person_role": "сценарист",
        "person_id": "person_test_20",
        "person_full_name": "Иванов Денис Денисович",
    },
    {
        "person_role": "сценарист",
        "person_id": "person_test_21",
        "person_full_name": "Петров Егор Егорович",
    },
]
db_rows_genres = [
    {
        "genre_id": "genre_test_1",
        "genre_name": "комедия",
    },
    {
        "genre_id": "genre_test_2",
        "genre_name": "экшн",
    },
]


def test_movies_init_by_db_rows():
    db_rows = [
        {
            **db_rows_movies[0],
            **db_rows_actors[0],
            **db_rows_genres[0],
        },
        {
            **db_rows_movies[0],
            **db_rows_actors[1],
            **db_rows_genres[1],
        },
    ]

    movie = ElasticSearchMovie.init_by_db_rows(db_rows)

    assert movie.id == "test1"

    assert len(movie.actors) == 2
    assert len(movie.directors) == 0
    assert len(movie.writers) == 0

    assert len(movie.actors_names) == 2
    assert len(movie.directors_names) == 0
    assert len(movie.writers_names) == 0

    assert len(movie.genres) == 2


def test_movies_init_by_db_rows_check_unique_lists():
    db_rows = [
        {**db_rows_movies[0], **db_rows_actors[0], **db_rows_genres[0]},
        {**db_rows_movies[0], **db_rows_directors[0], **db_rows_genres[0]},
        {**db_rows_movies[0], **db_rows_writers[0], **db_rows_genres[0]},
        {**db_rows_movies[0], **db_rows_actors[1], **db_rows_genres[1]},
        {**db_rows_movies[0], **db_rows_directors[1], **db_rows_genres[1]},
        {**db_rows_movies[0], **db_rows_writers[1], **db_rows_genres[1]},
        # дубли персон и жанров
        {**db_rows_movies[0], **db_rows_actors[0], **db_rows_genres[1]},
        {**db_rows_movies[0], **db_rows_directors[1], **db_rows_genres[0]},
        {**db_rows_movies[0], **db_rows_writers[1], **db_rows_genres[1]},
    ]

    movie = ElasticSearchMovie.init_by_db_rows(db_rows)

    assert len(movie.actors) == 2
    assert len(movie.directors) == 2
    assert len(movie.writers) == 2

    assert len(movie.actors_names) == 2
    assert len(movie.directors_names) == 2
    assert len(movie.writers_names) == 2

    assert len(movie.genres) == 2
