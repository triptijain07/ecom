FROM python:3.12-slim
WORKDIR /app
# Install build dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8006
CMD ["python", "manage.py", "runserver", "0.0.0.0:8006"]
