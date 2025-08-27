
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV ENV=dev

WORKDIR /

# Install system dependencies and setuptools
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt requirements-dev.txt /
RUN pip install -r requirements.txt
RUN pip install -r requirements-dev.txt

COPY /DashAI/back /DashAI/back
COPY /tests /tests
COPY DashAI/__init__.py /DashAI/__init__.py
COPY DashAI/__main__.py /DashAI/__main__.py

ENTRYPOINT ["python", "-m", "DashAI"]
