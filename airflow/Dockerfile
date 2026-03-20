FROM apache/airflow:2.9.3

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /tmp/airflow-etl-requirements.txt
RUN pip install --no-cache-dir -r /tmp/airflow-etl-requirements.txt
