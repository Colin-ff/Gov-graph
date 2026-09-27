# GovGraph backend (Flask + SQLAlchemy).
# Runs the app factory, which auto-creates tables and seeds initial data on
# startup, then serves the REST API on :5000.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=wsgi

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source so the image is self-contained; a bind mount overlays this in
# dev (see docker-compose.yml) to enable hot reload.
COPY . .

EXPOSE 5000

# --debug enables the reloader so edits under the bind mount take effect live.
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000", "--debug"]
