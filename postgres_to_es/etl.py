import functools
import logging

from etl.extractor import PgExtractor
from etl.loader import ESLoader
from etl.state import State, JsonFileStorage
from etl.entities import (Movie, Actor, Director, Writer, Person)

pg_extractor = PgExtractor()
es_loader = ESLoader()
state = State(JsonFileStorage())

upload_buffer = []


def coroutine(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        fn = func(*args, **kwargs)
        next(fn)
        return fn
    return inner


# генератор, вытаскивает данные пачками, пока данные не закончатся
def extract(target, modified_default='', batch_size=100):
    if modified_default:
        state.set_state('movies.modified', modified_default)
    if not state.get_state('movies.modified'):
        state.set_state('movies.modified', '2000-01-01 00:00:00')
    if not state.get_state('movies.offset'):
        state.set_state('movies.offset', 0)

    try:
        while True:
            modified = state.get_state('movies.modified')
            offset = state.get_state('movies.offset')

            # возвращает [(<movie_id>, <movie_modified>), ...]
            data = pg_extractor.get_changed_movie_ids(modified=modified, limit=batch_size, offset=offset)

            logging.info(
                "The data has been extracted. Params: modified >= {} LIMIT {} OFFSET {}. Amount {}".format(
                    modified, batch_size, offset, len(data))
            )

            if data:
                last_modified = state.get_state('movies.modified')
                if last_modified == str(data[-1][1].strftime("%Y-%m-%d %H:%M:%S.%f")):
                    offset = int(state.get_state('movies.offset') or 0)
                    state.set_state('movies.offset', offset + len(data))
                else:
                    state.set_state('movies.offset', 0)

                state.set_state(
                    'movies.modified',
                    str(data[-1][1].strftime("%Y-%m-%d %H:%M:%S.%f"))
                )

            target.send(tuple(map(lambda item: item[0], data)))
    except StopIteration:
        logging.warning("Extraction stopped")


@coroutine
def enrich(target):
    try:
        while ids := (yield):
            data = pg_extractor.get_movies_by_ids(ids)

            logging.info("The data has been enriched. Number of rows received {}".format(len(data)))

            target.send(data)
    except StopIteration:
        logging.warning("Extraction stopped")


def _get_person_object(row):
    person_classes_map = {
        'актёр': Actor,
        'директор': Director,
        'режисёр': Director,
        'сценарист': Writer,
    }

    person_class = person_classes_map.get(row["person_role"], None)
    if not person_class:
        logging.error("Can't handle role type '{}'".format(row["person_role"]))
        return None

    return person_class(
        id=row["person_id"],
        name=row["person_full_name"]
    )

def _get_unique(persons: list[Person]):
    uniq = {}
    for person in persons:
        uniq.setdefault(person.id, person)

    return list(uniq.values())


@coroutine
def transform(target):
    while data := (yield):

        # схлопываем развёрнутые после джойнов строки sql в объекты dataclasses
        movies = {}
        for item in data:
            movie = movies.setdefault(
                item["movie_id"],
                Movie(
                    id=item["movie_id"],
                    title=item["title"],
                    description=item["description"],
                    imdb_rating=item["rating"],
                    type=item["type"],
                )
            )

            person = _get_person_object(item)
            if isinstance(person, Actor):
                movie.actors.append(person)
            elif isinstance(person, Director):
                movie.directors.append(person)
            elif isinstance(person, Writer):
                movie.writers.append(person)

            movie.genres.append(item["genre"])

        # убираем дубли у всех сущностей
        for movie in movies.values():
            movie.actors = _get_unique(movie.actors)
            movie.directors = _get_unique(movie.directors)
            movie.writers = _get_unique(movie.writers)

            movie.genres = list(set(movie.genres))

        logging.info("Transformed {} sql rows into {} objects".format(len(data), len(movies)))

        target.send(list(movies.values()))


@coroutine
def buffer(target, batch_size=1000):
    global upload_buffer
    while data := (yield):
        if data and isinstance(data, list):
            upload_buffer += data

        if len(upload_buffer) >= batch_size:
            logging.info("The buffer for {} elements has been successfully formed. "
                         "The data will be transferred further along the pipeline. ".format(len(upload_buffer)))
            target.send(upload_buffer)
            upload_buffer = []


@coroutine
def load():
    while data := (yield):
        logging.info("load {}".format(len(data)))
        # target.send("ok")


def main():
    # основной pipe на корутинах - вытаскивает данные из PG, трансформирует, буферезует и загружает в ES
    try:
        extract(
            enrich(
                transform(
                    buffer(load(), batch_size=1000)
                ),
            ),
            batch_size=100
        )
    except StopIteration:
        pass

    # доборный pipe - проталкивает в ES то что осталось в буфере
    pipe_tail = buffer(load(), batch_size=1)
    pipe_tail.send(1)
    pipe_tail.close()


if __name__ == '__main__':
    logging.basicConfig(filename='logs/etl.log', level=logging.INFO)
    main()

