import functools
import logging

from etl.extractor import PgExtractor
from etl.loader import ESLoader
from etl.state import State, JsonFileStorage

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


@coroutine
def transform(target):
    while data := (yield):
        logging.info("transform {}".format(len(data)))
        # print("transform {}".format(data))

        target.send(data)


@coroutine
def buffer(target, batch_size=1000):
    global upload_buffer
    while data := (yield):
        if data and isinstance(data, list):
            upload_buffer += data

        if len(upload_buffer) >= batch_size:
            # logging.info("buffer {}".format(len(upload_buffer)))
            target.send(upload_buffer)
            upload_buffer = []


@coroutine
def load():
    while data := (yield):
        logging.info("load {}".format(len(data)))
        # target.send("ok")


# def pipe(coroutines: list):
#     built = None
#     for f in reversed(coroutines):
#         if built is None:
#             built = f()
#         else:
#             built = f(built)
#     return built


def main():
    # if state.get_state('movies.modified'):
    #     last_modified = state.get_state('movies.modified')
    # else:
    #     last_modified = '2000-01-01 00:00:00'
    #
    # if state.get_state('movies.offset'):
    #     offset = state.get_state('movies.offset')
    # else:
    #     offset = 0

    # while pg_extractor.has_new_data(start=last_modified, limit=extractor_limit, offset=offset):

    # основной pipe на корутинах - вытаскивает данные из PG, трансформирует, буферезует и загружает в ES
    try:
        extract(
            enrich(
                transform(
                    buffer(load(), batch_size=5000)
                ),
            ),
            batch_size=10
        )
    except StopIteration:
        pass

    # проталкивает в ES то что осталось в буфере
    pipe_tail = buffer(load(), batch_size=1)
    pipe_tail.send(1)
    pipe_tail.close()


if __name__ == '__main__':
    logging.basicConfig(filename='logs/etl.log', level=logging.DEBUG)

    # p = pipe([init_loop, extract, set_state, transform, buffer, load])
    main()

