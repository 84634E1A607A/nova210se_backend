#! /bin/sh

python manage.py migrate
daphne backend.asgi:application -p 80 -b 0.0.0.0
