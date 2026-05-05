#!/usr/bin/env bash
set -e

export ENV_NAME="${ENV_NAME:-production}"
export PORT="${PORT:-8000}"
export WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
export GUNICORN_THREADS="${GUNICORN_THREADS:-4}"
export GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"

exec gunicorn -c gunicorn.conf.py app:app
