FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependencies first so Docker caches this layer between builds.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# SQLite lives on a mounted volume in the cloud - set DB_PATH=/data/newsbot.db
# (docker-compose.yml already does this; on Railway/Render attach a volume).
CMD ["python", "main.py"]
