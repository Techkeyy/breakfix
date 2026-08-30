FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/breakfix
COPY breakfix ./breakfix
COPY pyproject.toml ./pyproject.toml
COPY README.md ./README.md

RUN pip install --no-cache-dir .

USER 65532:65532
