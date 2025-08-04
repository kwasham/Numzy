FROM python:3.11-slim

WORKDIR /app

COPY ./requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY ./app /app/app
COPY ./alembic.ini /app/alembic.ini
COPY ./migrations /app/migrations

ENV PYTHONPATH="/app"

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]