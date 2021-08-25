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
DOCKER_nginx=nginx

.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z0-9_\-\/]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo "(Other less used targets are available, open Makefile for details)"

dev_setup:	## развернуть Приложение для разработки (запускать один раз)
	@cp movies_admin/.env.example movies_admin/.env
	@docker/build
	@app/init
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

#
# Nginx
#

nginx/bash:		## доступ в контейнер c Nginx
	$(DOCKER_COMPOSE) exec $(DOCKER_NGINX) bash
.PHONY: nginx/bash

nginx/log:		## посмотреть логи контейнера Nginx
	$(DOCKER_COMPOSE) logs --follow $(DOCKER_NGINX)
.PHONY: nginx/log

