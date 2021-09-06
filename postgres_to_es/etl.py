import argparse
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

parser = argparse.ArgumentParser(
    prog='etl',
    description='Script for exporting data from PostgreSQL to ElasticSearch',
    allow_abbrev=False,
)
parser.add_argument(
    '--log_level',
    type=str,
    help='Set the logging leve',
    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
    default='WARNING',
)
parser.add_argument(
    '--start_date',
    type=str,
    help='Date from which the data import will start, if there is no memorized state ',
    default='2000-01-01 00:00:00',
)
args = parser.parse_args()


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
        state.set_state('movies.extractor.modified', modified_default)
    if state.get_state('movies.loader.modified') and not state.get_state('movies.extractor.modified'):
        state.set_state('movies.extractor.modified', state.get_state('movies.loader.modified'))
    if not state.get_state('movies.extractor.modified'):
        state.set_state('movies.extractor.modified', args.start_date)
    if not state.get_state('movies.offset'):
        state.set_state('movies.offset', 0)

    try:
        while True:
            modified = state.get_state('movies.extractor.modified')
            offset = state.get_state('movies.offset')

            # возвращает [(<movie_id>, <movie_modified>), ...]
            data = pg_extractor.get_changed_movie_ids(modified=modified, limit=batch_size, offset=offset)

            logging.info("The data has been extracted. Params: modified >= %s " +
                         "LIMIT %d OFFSET %d. Amount %d", modified, batch_size, offset, len(data))

            if data:
                last_modified = state.get_state('movies.extractor.modified')
                if last_modified == str(data[-1][1].strftime("%Y-%m-%d %H:%M:%S.%f")):
                    offset = int(state.get_state('movies.offset') or 0)
                    state.set_state('movies.offset', offset + len(data))
                else:
                    state.set_state('movies.offset', 0)

                state.set_state(
                    'movies.extractor.modified',
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

            logging.info("The data has been enriched. Number of rows received %d", len(data))

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
        logging.error("Can't handle role type '%s'", row["person_role"])
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
                    modified=item['modified'].strftime("%Y-%m-%d %H:%M:%S.%f"),
                )
            )

            person = _get_person_object(item)
            persons_map = {
                'Actor': movie.actors,
                'Director': movie.directors,
                'Writer': movie.writers,
            }
            persons_container = persons_map.get(person.__class__.__name__, None)
            if isinstance(persons_container, list):
                persons_container.append(person)

            movie.genres.append(item["genre"])

        # убираем дубли у всех сущностей
        for movie in movies.values():
            movie.actors = _get_unique(movie.actors)
            movie.directors = _get_unique(movie.directors)
            movie.writers = _get_unique(movie.writers)

            movie.genres = list(set(movie.genres))

        # добавляем списки имён актёров, режисёров, сценаристов
        for movie in movies.values():
            movie.actors_names = list(map(lambda item: item.name, movie.actors))
            movie.directors_names = list(map(lambda item: item.name, movie.directors))
            movie.writers_names = list(map(lambda item: item.name, movie.writers))

        logging.info("Transformed %d sql rows into %d objects", len(data), len(movies))

        target.send(list(movies.values()))


@coroutine
def buffer(target, batch_size=1000):
    # без глобальной переменной не работает
    # нужно где-то держать данные между двумя отдельныйми пайплайнами
    global upload_buffer
    while data := (yield):
        if data and isinstance(data, list):
            upload_buffer += data

        if len(upload_buffer) >= batch_size:
            logging.info("The buffer for %d elements has been successfully formed. " +
                         "The data will be transferred further along the pipeline. ", len(upload_buffer))
            target.send(upload_buffer)
            upload_buffer = []


@coroutine
def load(index_name=''):
    while movies_dataclasses := (yield):
        if movies_dataclasses and index_name:
            logging.info("%d records will be uploaded to ElasticSearch", len(movies_dataclasses))
            logging.debug(movies_dataclasses[0])

            res = es_loader.load_to_es(movies_dataclasses, index_name)
            if not res:
                raise StopIteration

            state.set_state('movies.loader.modified', movies_dataclasses[-1].modified)

        else:
            logging.warning("There is no records for upload or ElasticSearch index name is undefined")


def main():
    # основной pipe на корутинах - вытаскивает данные из PG, трансформирует, буферезует и загружает в ES
    try:
        extract(
            enrich(
                transform(
                    buffer(
                        load(index_name='movies'), batch_size=5000
                    )
                ),
            ),
            batch_size=1000
        )
    except StopIteration:
        logging.info("Done. The pipeline has run out of data.")

    # доборный pipe - проталкивает в ES то что осталось в буфере
    try:
        pipe_tail = buffer(load(index_name='movies'), batch_size=1)
        pipe_tail.send(1)
    except StopIteration:
        logging.info("Done. Additional pipeline has run out of data.")
    finally:
        pipe_tail.close()

    return True


if __name__ == '__main__':
    logging.basicConfig(filename='logs/etl.log', level=logging.getLevelName(args.log_level))
    main()

