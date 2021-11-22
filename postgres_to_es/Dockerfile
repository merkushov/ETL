FROM python:3.9.7-slim-bullseye

# Нам нужно создать пользователя с таким же UID
# как и у хостового пользователя
ARG uid=1000
ARG gid=100

RUN groupadd -g $gid devuser && \
    useradd -d /home/devuser -s /bin/bash -u $uid -g $gid devuser && \
    mkdir /home/devuser && \
    chown -R devuser:devuser /home/devuser

ENV PATH="/home/devuser/.local/bin:${PATH}"

RUN apt-get update
RUN apt-get install -y gcc musl-dev libpq-dev
RUN apt-get install -y vim make curl git tree jq

RUN mkdir /usr/src/postgres_to_es
RUN chown -R devuser:devuser /usr/src/postgres_to_es

USER devuser

WORKDIR /usr/src/postgres_to_es

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip
RUN pip install -r ./requirements.txt

COPY --chown=devuser:devuser . .

