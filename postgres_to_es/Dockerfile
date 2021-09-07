FROM python:3.9.7-slim-bullseye

WORKDIR /usr/src/postgres_to_es

RUN apt-get update
RUN apt-get install -y gcc musl-dev libpq-dev

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip
RUN pip install -r ./requirements.txt

COPY . .