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
