FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY core ./core
COPY integrations ./integrations
COPY server.py __main__.py ./

RUN useradd --create-home --uid 10001 appuser
USER appuser

ENTRYPOINT ["python", "-m", "server"]
