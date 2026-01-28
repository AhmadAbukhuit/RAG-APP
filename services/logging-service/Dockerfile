FROM python:3.12-slim

WORKDIR /app

COPY ./services/logging-service/requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

COPY ./shared ./shared
COPY ./services/logging-service/app .

# Start the application using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]