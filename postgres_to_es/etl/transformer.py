from etl.entities import ElasticSearchMovie

class ETLTransformer:
    def __init__(self, source_unique_key: str):
        self.source_unique_key = source_unique_key

    def transform(self):
        pass


class PGtoESMoviesTransformer(ETLTransformer):
    def transform(self, db_raw_data: list):
        # схлопываем развёрнутые после джойнов строки sql в объекты dataclasses
        db_rows_by_movie_ids = {}
        for item in db_raw_data:
            db_rows_by_movie_ids.setdefault(item[self.source_unique_key], [])
            db_rows_by_movie_ids[item[self.source_unique_key]].append(item)

        unique_objects = list()
        for db_rows in db_rows_by_movie_ids.values():
            unique_objects.append( ElasticSearchMovie.init_by_db_rows(list(db_rows)) )

        return unique_objects