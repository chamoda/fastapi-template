# Project

## Development

### Requirements

- Python 3.12
- Postgresql 16
- [uv](https://docs.astral.sh/uv/)

### Getting started

Following instructions are for Ubuntu 24.04 LTS.

- Clone the project
- Run `uv sync` to create virtual environment and install dependencies.
- Create postgresql database called `project_template`
- Run `cp .env.example .env` and update `.env` with correct configs.
- Run `uv run alembic upgrade head` to run database migrations.
- Run `uv run pre-commit install` to install pre-commit hooks. You can also run `uv run pre-commit run --all` to run and fix possible issues at once for all files.

### Best practices

- Always use `async` funtions in router files.
- All functions that handle any kind of IO from functions like (network requests to external serverices, disk reads/write) need to be `async` functions.

### Run dev server

`uv run fastapi dev`

### Run any custom commands

`uv run python manage.py --help`

### How to create and run migrations

#### Create migration files

`uv run alembic revision --autogenerate`

#### Update database with migration

`uv run alembic upgrade head`

### API documentation

API is documeneted in swagger endpoints accesible with `docs` url endpoint. For example http://localhost:8000/mobile/docs
