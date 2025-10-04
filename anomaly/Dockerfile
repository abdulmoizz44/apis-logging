FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY anomaly_requirements.txt .
RUN pip install --no-cache-dir -r anomaly_requirements.txt

# Copy the anomaly detector
COPY anomaly_detector.py .

# Create a non-root user
RUN useradd -m -u 1000 anomalydetector && chown -R anomalydetector:anomalydetector /app
USER anomalydetector

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://loki:3100/ready', timeout=5)" || exit 1

CMD ["python", "anomaly_detector.py"]
