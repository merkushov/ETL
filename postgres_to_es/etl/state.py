import abc
from typing import Any, Optional
import os.path
import json


class BaseStorage:
    @abc.abstractmethod
    def save_state(self, state: dict) -> None:
        """Сохранить состояние в постоянное хранилище"""
        pass

    @abc.abstractmethod
    def retrieve_state(self) -> dict:
        """Загрузить состояние локально из постоянного хранилища"""
        pass


class JsonFileStorage(BaseStorage):
    def __init__(self, file_path: Optional[str] = './file_storage.json'):
        self.file_path = file_path

    def save_state(self, state: dict) -> None:
        old_state = self.retrieve_state()
        new_state = { **old_state, **state }
        with open(self.file_path, 'w') as outfile:
            json.dump(new_state, outfile)

        return 1

    def retrieve_state(self) -> dict:
        data = {}
        if os.path.isfile(self.file_path):
            with open(self.file_path) as json_file:
                data = json.load(json_file)

        return data


class State:
    """
    Класс для хранения состояния при работе с данными, чтобы постоянно не перечитывать данные с начала.
    Здесь представлена реализация с сохранением состояния в файл.
    В целом ничего не мешает поменять это поведение на работу с БД или распределённым хранилищем.
    """

    def __init__(self, storage: BaseStorage):
        self.storage = storage

    def set_state(self, key: str, value: Any) -> None:
        """Установить состояние для определённого ключа"""
        self.storage.save_state({key: value})

    def get_state(self, key: str) -> Any:
        """Получить состояние по определённому ключу"""
        # self.storage.retrieve_state().get(key, None)
        res = self.storage.retrieve_state()
        return res.get(key, None)
