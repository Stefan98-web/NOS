# --- Stage 1: Build ---
FROM python:3.11-alpine AS builder

RUN apk add --no-cache gcc musl-dev postgresql-dev

WORKDIR /app

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.11-alpine

WORKDIR /app

COPY --from=builder /install /usr/local

COPY main.py .

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]