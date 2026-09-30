FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY models.py .
COPY alembic ./alembic

USER nobody

CMD ["alembic", "upgrade", "head"]
