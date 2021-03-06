from etl.entities import ElasticSearchGenre, ElasticSearchMovie, ElasticSearchPerson


class ETLTransformer:
    def __init__(self, source_unique_key: str):
        self.source_unique_key = source_unique_key

    def transform(self, db_raw_data: list):
        return db_raw_data


class PGtoESMoviesTransformer(ETLTransformer):
    def transform(self, db_raw_data: list):
        # схлопываем развёрнутые после джойнов строки sql в объекты dataclasses
        db_rows_by_movie_ids = {}
        for item in db_raw_data:
            db_rows_by_movie_ids.setdefault(item[self.source_unique_key], [])
            db_rows_by_movie_ids[item[self.source_unique_key]].append(item)

        unique_objects = list()
        for db_rows in db_rows_by_movie_ids.values():
            unique_objects.append(ElasticSearchMovie.init_by_db_rows(list(db_rows)))

        return unique_objects


class PGtoESGenresTransformer(ETLTransformer):
    def transform(self, db_raw_data: list):
        # схлопываем развёрнутые после джойнов строки sql в объекты dataclasses
        db_rows_by_genre_ids = {}
        for item in db_raw_data:
            db_rows_by_genre_ids.setdefault(item[self.source_unique_key], [])
            db_rows_by_genre_ids[item[self.source_unique_key]].append(item)

        unique_objects = list()
        for db_rows in db_rows_by_genre_ids.values():
            unique_objects.append(ElasticSearchGenre.init_by_db_rows(list(db_rows)))

        return unique_objects


class PGtoESPersonsTransformer(ETLTransformer):
    def transform(self, db_raw_data: list):
        # схлопываем развёрнутые после джойнов строки sql в объекты dataclasses
        db_rows_by_genre_ids = {}
        for item in db_raw_data:
            db_rows_by_genre_ids.setdefault(item[self.source_unique_key], [])
            db_rows_by_genre_ids[item[self.source_unique_key]].append(item)

        unique_objects = list()
        for db_rows in db_rows_by_genre_ids.values():
            unique_objects.append(ElasticSearchPerson.init_by_db_rows(list(db_rows)))

        return unique_objects
