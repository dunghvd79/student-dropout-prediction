# MLflow Tracking Server: backend store PostgreSQL, artifact store MinIO (S3)
FROM python:3.12-slim

RUN pip install --no-cache-dir \
    mlflow==2.19.0 \
    sqlalchemy==2.0.36 \
    alembic==1.14.0 \
    psycopg2-binary==2.9.10 \
    boto3==1.35.81

EXPOSE 5000
