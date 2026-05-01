FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/             ./shared/
COPY models/             ./models/
COPY app/                ./app/
COPY scripts/            ./scripts/
COPY websocket_server.py ./

ENV PYTHONPATH=/app

EXPOSE 8000

RUN adduser --disabled-password --no-create-home appuser
USER appuser

CMD ["uvicorn", "websocket_server:app", "--host", "0.0.0.0", "--port", "8000"]
