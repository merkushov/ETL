import logging
import os

import psycopg2
from psycopg2.extras import DictCursor

import etl.backoff


class PgExtractor:
    def __init__(self):
        pg_dns = {
            "dbname": os.environ.get("POSTGRES_DB"),
            "user": os.environ.get("POSTGRES_USER"),
            "password": os.environ.get("POSTGRES_PASSWORD"),
            "host": os.environ.get("POSTGRES_HOST"),
            "port": os.environ.get("POSTGRES_PORT"),
            "options": "-c search_path=content",
        }
        self.conn = psycopg2.connect(**pg_dns)

    def get_modified_ids():
        pass

    def get_data_by_ids():
        pass


class PgMovieExtractor(PgExtractor):
    @etl.backoff.on_exception()
    def get_modified_ids(self, modified: str, limit: int, offset: int):
        cur = self.conn.cursor()

        sql = """
            SELECT
                id, modified
            FROM
                content.movies
            WHERE
                modified >= %s
            ORDER BY modified
            LIMIT %s
            OFFSET %s
        """
        logging.debug(sql % (modified, limit, offset))

        cur.execute(sql, (modified, limit, offset))
        res = cur.fetchall()

        cur.close()

        return res

    @etl.backoff.on_exception(border_sleep_time=1)
    def get_data_by_ids(self, ids: tuple):
        cur = self.conn.cursor(cursor_factory=DictCursor)

        sql = """
            SELECT
                m.id AS movie_id,
                m.title,
                m.description,
                m.rating,
                mt.name as type,
                m.created,
                m.modified,
                pr.name as person_role,
                p.id as person_id,
                p.full_name as person_full_name,
                g.id as genre_id,
                g.name as genre_name
            FROM content.movies m
                LEFT JOIN content.movie_person_role mpr ON m.id=mpr.movie_id
                LEFT JOIN content.person_roles pr ON mpr.person_role_id=pr.id
                LEFT JOIN content.persons p ON mpr.person_id=p.id
                LEFT JOIN content.movie_genre mg ON m.id=mg.movie_id
                LEFT JOIN content.genres g ON mg.genre_id=g.id
                LEFT JOIN content.movie_types mt ON m.type_id=mt.id
            WHERE m.id IN %s
        """

        cur.execute(sql, (ids,))
        res = cur.fetchall()

        cur.close()

        return res


class PgGenreExtractor(PgExtractor):
    """
    Класс Экстрактор для извлечения данных о Жанрах из PostgreSQL
    """

    @etl.backoff.on_exception()
    def get_modified_ids(self, modified: str, limit: int, offset: int):
        """
        Метод для получения идентификаторов недавно модифицированных Жанров
        """
        cur = self.conn.cursor()

        sql = """
            SELECT
                id, modified
            FROM
                content.genres
            WHERE
                modified >= %s
            ORDER BY modified
            LIMIT %s
            OFFSET %s
        """
        logging.debug(sql % (modified, limit, offset))

        cur.execute(sql, (modified, limit, offset))
        res = cur.fetchall()

        cur.close()

        return res

    @etl.backoff.on_exception(border_sleep_time=1)
    def get_data_by_ids(self, ids: tuple):
        """
        Метод для получения необходимых данных по идентификаторам.
        Жёстко связан структурой данных с etl.transformer.PGtoESGenresTransformer
        и etl.entities.ElasticSearchGenre
        """
        cur = self.conn.cursor(cursor_factory=DictCursor)

        sql = """
            SELECT
                g.id as genre_id,
                g.name as genre_name,
                g.modified,
                m.id as movie_id,
                m.title as movie_title,
                m.rating as movie_rating
            FROM content.genres g
                LEFT JOIN content.movie_genre mg ON mg.genre_id=g.id
                LEFT JOIN content.movies m ON m.id=mg.movie_id
            WHERE g.id IN %s
        """

        cur.execute(sql, (ids,))
        res = cur.fetchall()

        cur.close()

        return res


class PgPersonExtractor(PgExtractor):
    """
    Класс Экстрактор для извлечения данных о Персонах из PostgreSQL
    """

    @etl.backoff.on_exception()
    def get_modified_ids(self, modified: str, limit: int, offset: int):
        """
        Метод для получения идентификаторов недавно модифицированных Персон
        """
        cur = self.conn.cursor()

        sql = """
            SELECT
                id, modified
            FROM
                content.persons
            WHERE
                modified >= %s
            ORDER BY modified
            LIMIT %s
            OFFSET %s
        """
        logging.debug(sql % (modified, limit, offset))

        cur.execute(sql, (modified, limit, offset))
        res = cur.fetchall()

        cur.close()

        return res

    @etl.backoff.on_exception(border_sleep_time=1)
    def get_data_by_ids(self, ids: tuple):
        """
        Метод для получения необходимых данных по идентификаторам.
        Жёстко связан структурой данных с etl.transformer.PGtoESPersonsTransformer
        и etl.entities.ElasticSearchPerson
        """
        cur = self.conn.cursor(cursor_factory=DictCursor)

        sql = """
            SELECT
                p.id AS person_id,
                p.full_name AS person_full_name,
                p.modified,
                pr.name AS person_role_name,
                m.id AS movie_id,
                m.title AS movie_title
            FROM content.persons p
                LEFT JOIN content.movie_person_role mpr ON mpr.person_id=p.id
                LEFT JOIN content.person_roles pr ON pr.id=mpr.person_role_id
                LEFT JOIN content.movies m ON m.id=mpr.movie_id
            WHERE p.id IN %s
        """

        cur.execute(sql, (ids,))
        res = cur.fetchall()

        cur.close()

        return res
