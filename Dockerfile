FROM python:3.7-slim

WORKDIR /usr/src/app

RUN pip install pipenv
COPY Pipfile Pipfile.lock ./
RUN pipenv sync

COPY setup.cfg setup.py README.rst alembic.ini ./
COPY alembic ./alembic
COPY mosbot ./mosbot
RUN pipenv run python setup.py develop

CMD ["/bin/sh", "-c", "pipenv run alembic upgrade head && pipenv run bot run"]
