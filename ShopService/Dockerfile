FROM python:3.12-slim

WORKDIR /app

# Install Spatialite + GDAL
RUN apt-get update && apt-get install -y \
    spatialite-bin \
    libsqlite3-mod-spatialite \
    gdal-bin \
    libgdal-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 8002 so Docker knows this container listens on 8002
EXPOSE 8002

# Run Django on port 8002 inside container
CMD ["python", "manage.py", "runserver", "0.0.0.0:8002"]


