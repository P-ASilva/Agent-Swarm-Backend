FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python -m app.infra.rag_pipeline.cli migrate && python -m message_persistence.cli migrate && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
