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

DOCKER_ES=es
DOCKER_ETL=etl

OS := $(shell uname)
.DEFAULT_GOAL := help

help:	## список доступных команд
	@grep -E '^[a-zA-Z0-9_\-\/]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo "(Other less used targets are available, open Makefile for details)"
.PHONY: help

#
# Работа с кодом
#

code/format: 	## принудительное форматирование кода по принятым стандартам
	$(DOCKER_COMPOSE) exec -T $(DOCKER_ETL) black ./
.PHONY: code/format

code/format_check: 	## проверка форматирования кода по принятым стандартам
	$(DOCKER_COMPOSE) exec -T $(DOCKER_ETL) black --check ./
.PHONY: code/format_check

code/isort:		## сортировка строк импорта
	$(DOCKER_COMPOSE) exec -T $(DOCKER_ETL) isort --profile black ./
.PHONY: code/isort

code/isort_check:		## проверка сортировок строк импорта
	$(DOCKER_COMPOSE) exec -T $(DOCKER_ETL) isort --check --profile black ./
.PHONY: code/isort_check

code/style:		## проверка стиля кода
	$(DOCKER_COMPOSE) exec -T $(DOCKER_ETL) flake8 --max-line-length 88 ./
.PHONY: code/style

code/check_all: code/format_check code/isort_check code/style	## статический анализ кода (без авто-исправлений) по принятым в проекте стандартам
.PHONY: code/check_all

code: code/format	code/isort code/style	## статический анализ кода и авто-исправления по принятым в проекте стандартам
.PHONY: code


# настройка .env переменных dev окружения
dev_env:
	@cp .env.example .env
	@cp postgres_to_es/.env.example postgres_to_es/.env

	# сгенерировать рандомные пароли для PostgreSQL
	# сгенерировать рандомный пароль для суперпользователя в Django
	# установить HOST_UID = UID текущего пользователя. Это влияет на UID пользователя внутри контейнера.
	# Нужно для совместимости прав доступа к сгенерированным файлам у хостового пользователя

	@if [[ $(OS) = 'Darwin' ]]; then \
		`env LC_CTYPE=C tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 10 | xargs -I '{}' sed -i '' 's/DJANGO_SUPERUSER_PASSWORD=[a-zA-Z0-9]*/DJANGO_SUPERUSER_PASSWORD={}/' .env`; \
		`id -u | xargs -I '{}' sed -i '' 's/HOST_UID=.*/HOST_UID={}/' .env`; \
		`sed -i '' 's/HOST_GID=.*/HOST_GID=61/' .env`; \
	elif [[ $(OS) = 'Windows_NT' ]]; then \
		`env LC_CTYPE=C cat /dev/urandom | tr -dc "a-zA-Z0-9" | head -c 10 | xargs -I '{}' sed -i -e 's/DJANGO_SUPERUSER_PASSWORD=[a-zA-Z0-9]*/DJANGO_SUPERUSER_PASSWORD={}/' .env`; \
		`id -u | xargs -I '{}' sed -i -e 's/HOST_UID=.*/HOST_UID={}/' .env`; \
		`id -g | xargs -I '{}' sed -i -e 's/HOST_GID=.*/HOST_GID={}/' .env`; \
	else \
		`env LC_CTYPE=C tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 10 | xargs -i sed -i 's/DJANGO_SUPERUSER_PASSWORD=[a-zA-Z0-9]*/DJANGO_SUPERUSER_PASSWORD={}/' .env`; \
		`id -u | xargs -i sed -i 's/HOST_UID=.*/HOST_UID={}/' .env`; \
		`id -g | xargs -i sed -i 's/HOST_GID=.*/HOST_GID={}/' .env`; \
	fi
.PHONY: dev_env

dev_setup:	## развернуть Приложение для разработки (запускать один раз)
	@make dev_env
	@make docker/destroy
	@make docker/build
	@make docker/up
	#@make db/waiting_for_readiness
	#@make app/init
	@make es/waiting_for_readiness
	@make etl/init
.PHONY: dev_setup

#
# Докер
#

docker/up:	## поднять Докер
	$(DOCKER_COMPOSE) up -d
.PHONY: docker/up

docker/start: docker/up 	## алиас для docker/up
.PHONY: docker/start

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
	$(DOCKER_COMPOSE) build
.PHONY: docker/build

docker/status:
	$(DOCKER_COMPOSE) ps
.PHONY: docker/status

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

etl/test: 	## авто-тесты
	$(DOCKER_COMPOSE) exec $(DOCKER_ETL) bash -c 'PYTHONPATH=. pytest -rP tests'
.Phony: etl/test

etl/pipe:	## запустить pipe перекачки данных из Pg в ES
	$(DOCKER_COMPOSE) exec $(DOCKER_ETL) python etl.py
.PHONY: etl/pipe

#
# ElasticSearch
#

es/bash:	## доступ в контейнер с ElasticSearch
	$(DOCKER_COMPOSE) exec $(DOCKER_ES) bash
.PHONY: es/bash

es/waiting_for_readiness:
	$(DOCKER_COMPOSE) exec $(DOCKER_ES) bash -c 'until curl --silent --output /dev/null http://localhost:9200/_cat/health?h=st; do printf "."; sleep 5; done; echo "ES ready."'
