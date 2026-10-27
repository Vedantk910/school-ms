# FastAPI backend (SQLModel + scikit-learn + SHAP)
# Build context is ./backend (see docker-compose.yml); paths below are relative to it.
FROM python:3.12-slim

WORKDIR /srv

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY app ./app
COPY seeds ./seeds
COPY tools ./tools

# Schema migrations (used by the `migrate` compose service)
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

# Trained-model artifacts live here (created by POST /ai/train)
RUN mkdir -p artifacts

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
