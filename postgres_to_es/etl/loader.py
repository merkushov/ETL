import json
import logging
import os
from typing import List
from urllib.parse import urljoin

import requests

import etl.backoff
from etl.entities import ElasticSearchEnityType, EnhancedJSONEncoder

logger = logging.getLogger()


class ESLoader:
    def __init__(self, index_name: str):
        self.url = os.environ.get("ELASTICSEARCH_URL", "")
        self.index_name = index_name

    @staticmethod
    def _get_es_bulk_query(
        rows: List[ElasticSearchEnityType], index_name: str
    ) -> List[str]:
        """
        Подготавливает bulk-запрос в Elasticsearch
        """
        prepared_query = []
        for row in rows:
            prepared_query.extend(
                [
                    json.dumps({"index": {"_index": index_name, "_id": row.id}}),
                    json.dumps(row, cls=EnhancedJSONEncoder),
                ]
            )
        return prepared_query

    @etl.backoff.on_exception()
    def load_to_es(self, records: List[ElasticSearchEnityType]):
        """
        Отправка запроса в ES и разбор ошибок сохранения данных
        """
        prepared_query = self._get_es_bulk_query(records, self.index_name)
        str_query = "\n".join(prepared_query) + "\n"

        response = requests.post(
            urljoin(self.url, "_bulk"),
            params={"filter_path": "items.*.error"},
            headers={"Content-Type": "application/x-ndjson"},
            data=str_query,
        )

        json_response = json.loads(response.content.decode())
        logging.debug(json_response)

        success = True
        for item in json_response.get("items", []):
            error_message = item["index"].get("error")
            if error_message:
                logger.error(error_message)
                success = False

        return success
