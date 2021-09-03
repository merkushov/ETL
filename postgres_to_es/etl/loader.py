from etl.entities import (Movie, EnhancedJSONEncoder)
from typing import List
from urllib.parse import urljoin
import json
import logging
import requests

logger = logging.getLogger()


class ESLoader:
    def __init__(self):
        self.url = "http://yandex_p_es:9200"

    def _get_es_bulk_query(self, rows: List[Movie], index_name: str) -> List[str]:
        """
        Подготавливает bulk-запрос в Elasticsearch
        """
        prepared_query = []
        for row in rows:
            prepared_query.extend([
                json.dumps({'index': {'_index': index_name, '_id': row.id}}),
                json.dumps(row, cls=EnhancedJSONEncoder)
            ])
        return prepared_query

    def load_to_es(self, records: List[Movie], index_name: str):
        """
        Отправка запроса в ES и разбор ошибок сохранения данных
        """
        prepared_query = self._get_es_bulk_query(records, index_name)
        str_query = '\n'.join(prepared_query) + '\n'

        response = requests.post(
            urljoin(self.url, '_bulk'),
            params={'filter_path': 'items.*.error'},
            headers={'Content-Type': 'application/x-ndjson'},
            data=str_query,
        )

        json_response = json.loads(response.content.decode())

        for item in json_response.get('items', []):
            error_message = item['index'].get('error')
            if error_message:
                logger.error(error_message)

