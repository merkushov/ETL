import argparse
import logging
import signal
import sys
import time

from etl.extractor import (PgMovieExtractor, PgPersonExtractor)
from etl.transformer import (PGtoESMoviesTransformer, PGtoESPersonsTransformer)
from etl.loader import ESLoader
from etl.state import State, JsonFileStorage
from etl.pipes import PipeEETBL
from etl.settings import settings

def main(from_date: str):
    pipes_config = [
        {
            "label": "Movies. Export from PG to ES",
            "extractor": PgMovieExtractor(),
            "loader": ESLoader(index_name="movies"),
            "states_keeper": State(JsonFileStorage(), key_prefix="movies.pg_to_es."),
            "transformer": PGtoESMoviesTransformer(source_unique_key="movie_id"),
            "extractor_batch_size": 1000,
            "loader_batch_size": 5000,
        },
        {
            "label": "Persons. Export from PG to ES",
            "extractor": PgPersonExtractor(),
            "loader": ESLoader(index_name="persons"),
            "states_keeper": State(JsonFileStorage(), key_prefix="persons.pg_to_es."),
            "transformer": PGtoESPersonsTransformer(source_unique_key="person_id"),
            "extractor_batch_size": 100,
            "loader_batch_size": 1000,
        }
    ]

    for pipe_conf in pipes_config:
        pipe = PipeEETBL(**pipe_conf)

        logging.info("Launching a new pipeline: %s", pipe_conf["label"])
        pipe.pump(from_date=from_date)
        logging.info("Pipeline data pumping completed")

    return True


def sigcatch(signum, frame):
    logging.info("A shutdown signal (%s) was caught. Shutting down...", signum)
    sys.exit()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigcatch)
    signal.signal(signal.SIGTERM, sigcatch)

    parser = argparse.ArgumentParser(
        prog="etl",
        description="Script for exporting data from PostgreSQL to ElasticSearch",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--log_level",
        type=str,
        help="Set the logging leve",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="WARNING",
    )
    parser.add_argument(
        "--from_date",
        type=str,
        help="Forces the export of data to start from the specified modification date",
    )
    args = parser.parse_args()

    logging.basicConfig(filename="logs/etl.log", level=logging.getLevelName(args.log_level))

    while True:
        main(from_date=args.from_date)

        logging.debug("Fall asleep for %d seconds ", settings.sleep_time)
        time.sleep(settings.sleep_time)
