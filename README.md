# ETL

## Как работать с Проектом

```shell
git clone git@github.com:merkushov/ETL.git
cd ETL

# (devel) Развернуть код в контейнерах Докер
make dev_setup

# (test) сгенерировать фейковые данные
make app/fake_data

# однократно запустить pipe по перекачке данных из Pg в ES
make etl/pipe

# закрыть контейнеры и удалить данные
make docker/destroy
```

Пояснения:
- Триггеры на уровне БД следят за изменением сущностей, связанных с Фильмами. В случае любых изменений обновляется поле movies.modified
- Для ETL процесса поднят отдельный Сервис в контейнере Докер.
- ETL процесс отслеживает изменения поля movies.modified и в случае изменений переливает данные из PostgreSQL в ElasticSearch

## Проверить хранилище

```shell
curl -XGET http://localhost:9200/_cat/indices
curl -XGET http://localhost:9200/movies/_search
curl -XGET http://localhost:9200/persons/_search
curl -XGET http://localhost:9200/genres/_search
```
