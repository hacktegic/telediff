FROM python:3.13-slim

WORKDIR /app

COPY dist/telediff*.whl /app

RUN groupadd -r telediff && useradd -d /app -r -g telediff telediff && \
    chown -R telediff:telediff /app && \
    pip install --no-cache-dir /app/telediff*.whl

USER telediff