FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY insightsync/data/requirements.txt /tmp/data-requirements.txt
COPY insightsync/backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/data-requirements.txt -r /tmp/backend-requirements.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "insightsync.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
