#! /bin/sh

python manage.py migrate
daphne backend.asgi:application \
    -p 80 -b 0.0.0.0 \
    --verbosity 3 --access-log /var/log/access.log \
    --proxy-headers \
    --server-name Nova210SE_BE
