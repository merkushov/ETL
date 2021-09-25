import functools
import logging

from etl.settings import settings


def coroutine(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        fn = func(*args, **kwargs)
        next(fn)
        return fn

    return inner


# генератор, вытаскивает данные пачками, пока данные не закончатся
def extract(
    target,
    forced_modification_date: str,
    batch_size=100,
    extractor=object,
    state=object,
):
    if forced_modification_date:
        state.set_state("extractor.modified", forced_modification_date)
        state.set_state("offset", 0)
    if state.get_state("loader.modified") and not state.get_state("extractor.modified"):
        state.set_state("extractor.modified", state.get_state("loader.modified"))
    if not state.get_state("extractor.modified"):
        state.set_state("extractor.modified", settings.start_date)
    if not state.get_state("offset"):
        state.set_state("offset", 0)

    try:
        while True:
            modified = state.get_state("extractor.modified")
            offset = state.get_state("offset")

            # возвращает [(<movie_id>, <movie_modified>), ...]
            data = extractor.get_modified_ids(
                modified=modified, limit=batch_size, offset=offset
            )

            logging.info(
                "The data has been extracted. Params: modified >= %s "
                + "LIMIT %d OFFSET %d. Amount %d",
                modified,
                batch_size,
                offset,
                len(data),
            )

            if data:
                last_modified = state.get_state("extractor.modified")
                if last_modified == str(data[-1][1].strftime("%Y-%m-%d %H:%M:%S.%f")):
                    offset = int(state.get_state("offset") or 0)
                    state.set_state("offset", offset + len(data))
                else:
                    state.set_state("offset", 0)

                state.set_state(
                    "extractor.modified",
                    str(data[-1][1].strftime("%Y-%m-%d %H:%M:%S.%f")),
                )

            target.send(tuple(map(lambda item: item[0], data)))
    except StopIteration:
        logging.warning("Extraction stopped")


@coroutine
def enrich(target, extractor=object):
    try:
        while ids := (yield):
            data = extractor.get_data_by_ids(ids)

            logging.info(
                "The data has been enriched. Number of rows received %d", len(data)
            )

            target.send(data)
    except StopIteration:
        logging.warning("Extraction stopped")


@coroutine
def transform(target, transformer: object):
    while raw_data := (yield):
        transformed_objects = transformer.transform(raw_data)

        logging.info(
            "Transformed %d sql rows into %d objects",
            len(raw_data),
            len(transformed_objects),
        )

        target.send(transformed_objects)


def build_buffer():
    upload_buffer = []

    @coroutine
    def buffer(target, batch_size=1000):
        nonlocal upload_buffer
        while data := (yield):
            if data and isinstance(data, list):
                upload_buffer += data

            if len(upload_buffer) >= batch_size:
                logging.info(
                    "The buffer for %d elements has been successfully formed. "
                    + "The data will be transferred further along the pipeline. ",
                    len(upload_buffer),
                )
                target.send(upload_buffer)
                upload_buffer = []

    return buffer


@coroutine
def load(loader=object, state=object):
    while dataclasses_objects := (yield):
        logging.info(
            "%d records will be uploaded to ElasticSearch", len(dataclasses_objects)
        )

        res = loader.load_to_es(dataclasses_objects)
        if not res:
            raise StopIteration

        state.set_state("loader.modified", dataclasses_objects[-1].modified)


class PipeEETBL:
    """
    Класс формурующий конкретныйы Пайплайн.
      - extract - вытащить список id объектов, которые были модифицированы
      - enrich - обогатить данные, достав всю необходимую информацию по объекту
            и по связанным сущностям
      - transform - переформатировать данные из строк полученных из Источника
            в объекты пригодные для загрузки в Приёмник
      - buffer - буферизовать поступающие данные
      - load - отправить данные в Приёмник
    """

    def __init__(
        self,
        label: str,
        extractor: object,
        loader: object,
        transformer: object,
        states_keeper: object,
        extractor_batch_size=100,
        loader_batch_size=1000,
    ):
        self.label = label
        self.extractor = extractor
        self.loader = loader
        self.transformer = transformer
        self.states_keeper = states_keeper
        self.extractor_batch_size = extractor_batch_size
        self.loader_batch_size = loader_batch_size

    def pump(self, from_date: str):
        buffer = build_buffer()

        # основной pipe на корутинах - вытаскивает данные из Источника,
        # трансформирует, буферезует и загружает в Приёмник.
        # Останавливается, когда данные закончились.
        try:
            extract(
                enrich(
                    transform(
                        buffer(
                            load(
                                loader=self.loader,
                                state=self.states_keeper,
                            ),
                            batch_size=self.loader_batch_size,
                        ),
                        transformer=self.transformer,
                    ),
                    extractor=self.extractor,
                ),
                forced_modification_date=from_date,
                extractor=self.extractor,
                state=self.states_keeper,
                batch_size=self.extractor_batch_size,
            )
        except StopIteration:
            logging.debug("Done. The pipeline has run out of data.")

        # доборный pipe - проталкивает в ES то что осталось в буфере
        try:
            pipe_tail = buffer(
                load(loader=self.loader, state=self.states_keeper), batch_size=1
            )
            pipe_tail.send(1)
        except StopIteration:
            logging.debug("Done. Additional pipeline has run out of data.")
        finally:
            pipe_tail.close()

        return True
