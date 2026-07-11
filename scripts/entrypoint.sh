#!/bin/sh
set -e

python - <<'PY'
import os
import socket
import time

services = [
    ("mysql", os.environ.get("DB_HOST", "mysql"), int(os.environ.get("DB_PORT", "3306"))),
    ("redis", os.environ.get("REDIS_HOST", "redis"), int(os.environ.get("REDIS_PORT", "6379"))),
]

for name, host, port in services:
    deadline = time.time() + 60
    while True:
        try:
            with socket.create_connection((host, port), timeout=3):
                print(f"{name} is available at {host}:{port}")
                break
        except OSError:
            if time.time() > deadline:
                raise RuntimeError(f"Timed out waiting for {name} at {host}:{port}")
            print(f"Waiting for {name} at {host}:{port}...")
            time.sleep(2)
PY

python manage.py migrate
python manage.py collectstatic --noinput

exec "$@"
