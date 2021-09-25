import os

import psycopg2
import pytest


def test_close_cursor():
    conn = psycopg2.connect(
        dbname=os.environ.get("POSTGRES_DB"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD"),
        host=os.environ.get("POSTGRES_HOST"),
        port=os.environ.get("POSTGRES_PORT"),
        options="-c search_path=content",
    )

    def get_some_data():
        cur = conn.cursor()
        cur.execute("SELECT 1")
        return True

    get_some_data()

    check = conn.closed
    assert check == 0
