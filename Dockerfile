FROM python:3.12-slim

RUN apt-get update -y
RUN apt-get install -y git gdal-bin python3-gdal build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info

WORKDIR /code
COPY requirements /code/requirements
RUN pip install -r requirements/development.txt --no-cache-dir

# Setup git hook pre-commit
COPY .pre-commit-config.yaml /code
COPY .git /code/.git
RUN pre-commit install --install-hooks

EXPOSE 8000
#
