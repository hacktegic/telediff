FROM python:3.13-slim
WORKDIR /app
COPY dist/telediff*.whl /app
RUN pip install --no-cache-dir /app/telediff*.whl
