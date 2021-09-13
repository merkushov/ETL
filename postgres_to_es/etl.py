import argparse
import functools
import logging

from etl.extractor import PgExtractor
from etl.loader import ESLoader
from etl.state import State, JsonFileStorage
from etl.entities import (ElasticSearchMovie, Actor, Director, Writer, Person)

pg_extractor = PgExtractor()
es_loader = ESLoader()
state = State(JsonFileStorage())

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

            # Идея с перемещением set_state под target.send() очень интересная. Я об этом не подумал.
            # Но это не поможет из-за того что не каждый проход pipe заканчивается загрузкой данных в ES
            # Есть шаг Буферизации данных, перед отправкой в ES.
            # Я держу два состояния
            #   - movies.extractor.modified (и movies.offset) - фиксирует текущее состояние выборки данных из PostgreSQL
            #   - movies.loader.modified - фиксирует загрузку данных в ES
            # Если загрузка в ES провалилась, генерируется исключение и весь pipe останавливается.
            # После повторного перезапуска состояние начинается от movies.loader.modified
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


@coroutine
def transform(target):
    while data := (yield):

        # схлопываем развёрнутые после джойнов строки sql в объекты dataclasses
        db_rows_by_movie_ids = {}
        for item in data:
            db_rows_by_movie_ids.setdefault(item["movie_id"], [])
            db_rows_by_movie_ids[item["movie_id"]].append(item)

        movies = list()
        for db_rows in db_rows_by_movie_ids.values():
            movies.append( ElasticSearchMovie.init_by_db_rows(list(db_rows)) )

        logging.info("Transformed %d sql rows into %d objects", len(data), len(movies))

        target.send(movies)


def build_buffer(target):
    upload_buffer = []

    @coroutine
    def buffer(batch_size=1000):
        nonlocal upload_buffer
        while data := (yield):
            if data and isinstance(data, list):
                upload_buffer += data

            if len(upload_buffer) >= batch_size:
                logging.info("The buffer for %d elements has been successfully formed. " +
                             "The data will be transferred further along the pipeline. ", len(upload_buffer))
                target.send(upload_buffer)
                upload_buffer = []

    return buffer


@coroutine
def load(index_name=''):
    while movies_dataclasses := (yield):
        if movies_dataclasses and index_name:
            logging.info("%d records will be uploaded to ElasticSearch", len(movies_dataclasses))

            res = es_loader.load_to_es(movies_dataclasses, index_name)
            if not res:
                raise StopIteration

            state.set_state('movies.loader.modified', movies_dataclasses[-1].modified)

        else:
            logging.warning("There is no records for upload or ElasticSearch index name is undefined")


def main():
    buffer_core = build_buffer(load(index_name='movies'))

    # основной pipe на корутинах - вытаскивает данные из PG, трансформирует, буферезует и загружает в ES
    try:
        extract(
            enrich(
                transform(
                    buffer_core(batch_size=5000)
                ),
            ),
            batch_size=1000
        )
    except StopIteration:
        logging.info("Done. The pipeline has run out of data.")

    # доборный pipe - проталкивает в ES то что осталось в буфере
    try:
        pipe_tail = buffer_core(batch_size=1)
        pipe_tail.send(1)
    except StopIteration:
        logging.info("Done. Additional pipeline has run out of data.")
    finally:
        pipe_tail.close()

    return True


if __name__ == '__main__':
    logging.basicConfig(filename='logs/etl.log', level=logging.getLevelName(args.log_level))
    main()

