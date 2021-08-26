import argparse
import json
import os

from elasticsearch import Elasticsearch

parser = argparse.ArgumentParser(
    prog='init_es',
    description='The script creates indexes in ElasticSearch according to the schema',
    allow_abbrev=False,
)
parser.add_argument(
    '--indexes_path',
    type=str,
    help='The path to the system folder with indexes. The file must be in JSON format. The file name in the folder is the name of the index',
    default='./es_indexes'
)
parser.add_argument(
    '-d',
    '--delete_if_exists',
    action=argparse.BooleanOptionalAction,
    help='Remove ElasticSearch index if exists',
    default=False,
)
args = parser.parse_args()

es = Elasticsearch([os.environ.get('ELASTICSEARCH_URL')])

files = [(os.path.join(args.indexes_path, f), f) for f in os.listdir(args.indexes_path) if os.path.isfile(os.path.join(args.indexes_path, f))]
for path, name in files:
    index_name = name[:-5]
    with open(path) as file:
        index_settings = json.load(file)

    if index_name and index_settings:
        if es.indices.exists(index_name):
            if args.delete_if_exists:
                es.indices.delete(index_name)
                print('"{}" index has been deleted'.format(index_name))
            else:
                print('Index "{}" already created'.format(index_name))

        if not es.indices.exists(index_name):
            print('Creating "{}" index...'.format(index_name))
            es.indices.create(index=index_name, body=index_settings)
            print('Index created')
