# CRIFCAN COLABORATIVO

Proyecto colaborativo

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## License

This project is licensed under the MIT License.

## Settings

Configuration settings have been moved to the [settings documentation](http://cookiecutter-django.readthedocs.io/en/latest/settings.html).

## Commands

### Activate Virtual Environment

```sh

$ python -m venv env

```

```sh
$ env\Scripts\activate
```

### Install Dependencies

```sh
$ pip install -r requirements.txt
```

### Database Migrations

```sh
$ python manage.py makemigrations
$ python manage.py migrate

```
```sh
$ python manage.py loaddata urls.json

```



### SuperUser Account

```sh
$ python manage.py createsuperuser
```


```sh
$ python manage.py runserver
```
### Test Coverage

```sh
$ coverage run -m pytest
$ coverage html
$ open htmlcov/index.html
```

### Running Tests with pytest

```sh
$ pytest
```