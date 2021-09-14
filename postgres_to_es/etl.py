import argparse
import logging

from etl.extractor import PgMovieExtractor
from etl.transformer import PGtoESMoviesTransformer
from etl.loader import ESLoader
from etl.state import State, JsonFileStorage
from etl.pipes import PipeEETBL

def main():
    pipes_config = [
        {
            "label": "Movies. Export from PG to ES",
            "extractor": PgMovieExtractor(),
            "loader": ESLoader(index_name='movies'),
            "states_keeper": State(JsonFileStorage(), key_prefix="movies.pg_to_es."),
            "transformer": PGtoESMoviesTransformer(source_unique_key="movie_id"),
            "extractor_batch_size": 1000,
            "loader_batch_size": 5000,
        }
    ]

    for pipe_conf in pipes_config:
        pipe = PipeEETBL(**pipe_conf)

        logging.info("Launching a new pipeline: %s", pipe_conf["label"])
        pipe.pump()
        logging.info("Pipeline data pumping completed")

    return True


if __name__ == '__main__':
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
        help='Date from which the data import will start, if there is no memorized state',
        default='2000-01-01 00:00:00',
    )
    args = parser.parse_args()

    logging.basicConfig(filename='logs/etl.log', level=logging.getLevelName(args.log_level))

    main()
