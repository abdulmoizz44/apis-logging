#!/bin/bash

echo "🚀 Starting Anomaly Detection System..."

# Create anomaly directory if it doesn't exist
mkdir -p anomaly

# Move files to correct locations
cp anomaly_detector.py anomaly/
cp anomaly_requirements.txt anomaly/

# Build and start services
cd monitoringg
echo "📦 Building and starting Docker services..."
docker-compose up --build -d

echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
echo "🔍 Checking service status..."
docker-compose ps

echo ""
echo "✅ Anomaly Detection System is running!"
echo ""
echo "📊 Access Grafana at: http://localhost:3000"
echo "   - Default login: admin/admin"
echo "   - Import the dashboard from: monitoringg/grafana-dashboard.json"
echo ""
echo "🔍 View logs with:"
echo "   docker-compose logs -f anomaly-detector"
echo ""
echo "🛑 Stop with:"
echo "   docker-compose down"
echo ""
echo "🧪 Test the system by hitting your app endpoints:"
echo "   curl http://localhost:5000/api/users"
echo "   curl http://localhost:5000/api/suspicious  # This will generate anomalies"
