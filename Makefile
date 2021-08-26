# silent by default
ifndef VERBOSE
.SILENT:
endif

ifeq ($(STAGE), prod)
DOCKER_COMPOSE_FILE=-f docker-compose.prod.yaml
else
DOCKER_COMPOSE_FILE=-f docker-compose.yaml
endif

DOCKER_COMPOSE=docker-compose $(DOCKER_COMPOSE_FILE)

DOCKER_APP=app
DOCKER_DB=db
DOCKER_NGINX=nginx
DOCKER_ES=es
DOCKER_ETL=etl

.DEFAULT_GOAL := help

help:	## список доступных команд
	@grep -E '^[a-zA-Z0-9_\-\/]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo "(Other less used targets are available, open Makefile for details)"

# настройка .env переменных dev окружения
dev_env:
	@cp movies_admin/.env.example movies_admin/.env
	@cp postgres_to_es/.env.example postgres_to_es/.env
	# сгенерировать рандомные пароли для PostgreSQL
	`env LC_CTYPE=C tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 42 | xargs -i sed -i 's/POSTGRES_PASSWORD=[a-zA-Z0-9]*/POSTGRES_PASSWORD={}/' movies_admin/.env postgres_to_es/.env`
	# сгенерировать рандомный пароль для суперпользователя в Django
	`env LC_CTYPE=C tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 10 | xargs -i sed -i 's/DJANGO_SUPERUSER_PASSWORD=[a-zA-Z0-9]*/DJANGO_SUPERUSER_PASSWORD={}/' movies_admin/.env`

dev_setup:	## развернуть Приложение для разработки (запускать один раз)
	@make dev_env
	@make docker/destroy
	@make docker/build
	@make docker/up
	@make db/waiting_for_readiness
	@make app/init
	@make es/waiting_for_readiness
	@make etl/init
.PHONY: dev_setup

#
# Приложение
#

app/init:	## инициализация Приложения
	$(DOCKER_COMPOSE) exec $(DOCKER_APP) python manage.py migrate --noinput
	$(DOCKER_COMPOSE) exec $(DOCKER_APP) python manage.py createsuperuser --noinput
	$(DOCKER_COMPOSE) exec $(DOCKER_APP) python manage.py compilemessages
	$(DOCKER_COMPOSE) exec $(DOCKER_APP) python manage.py collectstatic --no-input --clear
	$(DOCKER_COMPOSE) exec $(DOCKER_APP) python manage.py loaddata test_data.json
.PHONY: app/init

app/bash:		## доступ в контейнер с Django
	$(DOCKER_COMPOSE) exec $(DOCKER_APP) bash
.PHONY: app/bash

app/log:	## посмотреть логи контейнера Приложения
	$(DOCKER_COMPOSE) logs --follow $(DOCKER_APP)
.PHONY: app/log

app/test:	## test
	@echo $(STAGE)
.PHONY: app/test

#
# Докер
#

docker/up:	## поднять Докер
	$(DOCKER_COMPOSE) up -d
.PHONY: docker/up

docker/stop:	## остановить все контейнеры Приложения
	$(DOCKER_COMPOSE) stop
.PHONY: docker/stop

docker/down: 	## остановить и удалить все контейнеры Приложения
	$(DOCKER_COMPOSE) down --remove-orphans
.PHONY: docker/down

docker/destroy: 	## остановить/удалить контейнеры и очистить данные Приложения
	$(DOCKER_COMPOSE) down --volumes --remove-orphans
.PHONY: docker/destroy

docker/build:
	$(DOCKER_COMPOSE) build --no-cache --force-rm
.PHONY: docker/build

docker/status:
	$(DOCKER_COMPOSE) ps
.PHONY: docker/status

#
# База данных
#

db/bash:		## доступ в контейнер с БД
	$(DOCKER_COMPOSE) exec $(DOCKER_DB) bash
.PHONY: db/bash

db/log:		## посмотреть логи контейнера БД
	$(DOCKER_COMPOSE) logs --follow $(DOCKER_DB)
.PHONY: db/log

db/psql:		## интерактивный терминал PostgreSQL
	$(DOCKER_COMPOSE) exec $(DOCKER_DB) psql -U postgres movie_catalog
.PHONY: db/psql

db/waiting_for_readiness:
	$(DOCKER_COMPOSE) exec $(DOCKER_DB) bash -c 'until pg_isready 2>/dev/null; do sleep 1 ; done; echo "Database ready."'

#
# Nginx
#

nginx/bash:		## доступ в контейнер c Nginx
	$(DOCKER_COMPOSE) exec $(DOCKER_NGINX) bash
.PHONY: nginx/bash

nginx/log:		## посмотреть логи контейнера Nginx
	$(DOCKER_COMPOSE) logs --follow $(DOCKER_NGINX)
.PHONY: nginx/log

#
# ETL - Сервис по перекачиванию данных из PostgreSQL в ElasticSearch
#

etl/init:	## инициализирует ElasticSearch
	$(DOCKER_COMPOSE) exec $(DOCKER_ETL) bash -c 'python3 init_es.py'
.PHONY: etl/init

etl/bash:	## доступ в контейнер с ETL
	$(DOCKER_COMPOSE) exec $(DOCKER_ETL) bash
.PHONY: etl/bash

etl/log: 	## посмотреть логи контейнера etl
	$(DOCKER_COMPOSE) logs --follow $(DOCKER_ETL)
.PHONY: etl/log

#
# ElasticSearch
#

es/waiting_for_readiness:
	$(DOCKER_COMPOSE) exec $(DOCKER_ES) bash -c 'until curl --silent --output /dev/null http://localhost:9200/_cat/health?h=st; do printf "."; sleep 3; done; echo "ES ready."'
