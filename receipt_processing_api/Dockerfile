FROM python:3.11-slim

WORKDIR /code

COPY . /code

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]