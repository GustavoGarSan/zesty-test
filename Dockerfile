FROM python:3.9.1-slim

WORKDIR /zesty-test

COPY ./requirements.txt .

COPY ./zesty ./zesty

RUN apt-get update \
    && apt-get -y install libpq-dev gcc \
    && pip install psycopg2

RUN pip install -r requirements.txt

CMD ["python", "./zesty/app.py"]