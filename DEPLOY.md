# FINAL Lunch production deployment

## Local production run

python -m pip install -r requirements.txt
python -m pip install gunicorn
cp .env.example .env
bash start_production.sh

Health check:

curl -I http://127.0.0.1:8000/healthz

## Docker

docker build -t final-lunch:v2 .
docker run --rm -p 8000:8000 -e ENV_NAME=production -e SECRET_KEY=change-me final-lunch:v2

## Render / Railway start command

gunicorn -c gunicorn.conf.py app:app

## Required environment variables

ENV_NAME=production
SECRET_KEY=<long random secret>
PORT=<platform port>
DATABASE_PATH=instance/lunch_platform.db

Next scaling step: add PostgreSQL support via DATABASE_URL and migrations.
