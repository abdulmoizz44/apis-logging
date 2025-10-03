# Anomaly Detection Test Application

A Flask application designed to generate both normal and suspicious API logs for testing anomaly detection systems.

## Features

- **3 Normal Endpoints**: Generate typical API behavior patterns
- **1 Suspicious Endpoint**: Creates various anomaly patterns
- **Structured JSON Logging**: All requests logged in JSON format for easy analysis
- **Realistic Data**: Simulates a typical e-commerce API

## Endpoints

### Normal Endpoints
- `GET /api/users` - Returns user data (normal response times, 200 status)
- `GET /api/products` - Returns product catalog (normal response times, 200 status)  
- `GET /api/orders` - Returns order history (normal response times, 200 status)

### Suspicious Endpoint
- `GET|POST /api/suspicious` - Generates various anomaly patterns:
  - Random slow responses (2-5 seconds)
  - High error rates (400, 401, 403, 500 status codes)
  - Unusual response sizes
  - Suspicious user agents
  - High anomaly scores

### Utility
- `GET /api/health` - Health check endpoint

## Installation

### Option 1: Docker
```bash
# Build the image
docker build -t anomaly-detection-app .

# Run the container
docker run -p 5000:5000 anomaly-detection-app
```

### Option 2: Local Python
```bash
pip install -r requirements.txt
python app.py
```

The application will start on `http://localhost:5000`

## Log Format

All requests are logged in JSON format with the following structure:

```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "endpoint": "/api/users",
  "method": "GET",
  "status_code": 200,
  "response_time_ms": 25.5,
  "user_agent": "Mozilla/5.0...",
  "ip_address": "127.0.0.1",
  "request_id": "req_1704110400000",
  "user_count": 3
}
```

## Testing Anomaly Detection

1. **Generate Normal Traffic**: Hit the normal endpoints repeatedly
2. **Generate Suspicious Traffic**: Hit the suspicious endpoint to create anomalies
3. **Analyze Logs**: Use the structured JSON logs to train/test your anomaly detection model

## Example Usage

```bash
# Generate normal traffic
curl http://localhost:5000/api/users
curl http://localhost:5000/api/products
curl http://localhost:5000/api/orders

# Generate suspicious traffic
curl http://localhost:5000/api/suspicious
```

## Docker Features

- **Simple and lightweight** Dockerfile
- **Python 3.11-slim** base image
- **Optimized caching** with requirements.txt first

The logs will be output to stdout in JSON format, perfect for feeding into anomaly detection systems.
