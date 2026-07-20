FROM python:3.11-slim

WORKDIR /backend

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    swig \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app/ ./app/
RUN mkdir -p /tmp/face_db

EXPOSE 8000

CMD python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
