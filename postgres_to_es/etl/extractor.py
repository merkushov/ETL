import os
import logging
import psycopg2
from psycopg2.extras import DictCursor

import etl.backoff


class PgExtractor:
    def __init__(self):
        pg_dns = {
            'dbname': os.environ.get('POSTGRES_DB'),
            'user': os.environ.get('POSTGRES_USER'),
            'password': os.environ.get('POSTGRES_PASSWORD'),
            'host': os.environ.get('POSTGRES_HOST'),
            'port': os.environ.get('POSTGRES_PORT'),
            'options': '-c search_path=content',
        }
        self.conn = psycopg2.connect(**pg_dns)

    @etl.backoff.on_exception()
    def get_changed_movie_ids(self, modified: str, limit: int, offset: int):
        cur = self.conn.cursor()

        sql = "SELECT id, modified FROM content.movies WHERE modified >= %s ORDER BY modified LIMIT %s OFFSET %s"
        logging.debug(sql % (modified, limit, offset))

        cur.execute(sql, (modified, limit, offset))
        res = cur.fetchall()

        cur.close()

        return res

    @etl.backoff.on_exception(border_sleep_time=1)
    def get_movies_by_ids(self, ids: tuple):
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
                g.name as genre
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
