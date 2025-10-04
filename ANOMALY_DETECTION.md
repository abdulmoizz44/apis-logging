# Log Anomaly Detection System

A containerized ML-based anomaly detection system for your application logs using unsupervised learning algorithms.

## Features

- **Unsupervised ML**: Uses Isolation Forest and One-Class SVM algorithms
- **No External APIs**: Runs completely locally, no model API dependencies
- **Real-time Detection**: Analyzes logs every 60 seconds
- **Multiple Anomaly Types**: Detects response time, status code, and general behavioral anomalies
- **Grafana Integration**: Visualizes anomalies in real-time dashboards
- **Containerized**: Easy deployment with Docker Compose

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Flask App     │───▶│    Loki      │───▶│ Anomaly Detector│
│   (Logs)        │    │  (Storage)   │    │   (ML Analysis) │
└─────────────────┘    └──────────────┘    └─────────────────┘
                                │                    │
                                ▼                    ▼
                       ┌──────────────┐    ┌─────────────────┐
                       │   Promtail   │    │    Grafana      │
                       │ (Collection) │    │ (Visualization) │
                       └──────────────┘    └─────────────────┘
```

## ML Algorithms Used

1. **Isolation Forest**: General anomaly detection based on feature isolation
2. **One-Class SVM**: Specialized detection for response time anomalies
3. **One-Class SVM**: Specialized detection for status code anomalies

## Quick Start

1. **Start the system**:
   ```bash
   ./start_anomaly_detection.sh
   ```

2. **Access Grafana**:
   - URL: http://localhost:3000
   - Login: admin/admin
   - Import dashboard from `monitoringg/grafana-dashboard.json`

3. **Generate test data**:
   ```bash
   # Normal requests
   curl http://localhost:5000/api/users
   curl http://localhost:5000/api/products
   
   # Suspicious requests (will generate anomalies)
   curl http://localhost:5000/api/suspicious
   ```

## Configuration

### Anomaly Detection Parameters

Edit `anomaly_detector.py` to adjust:

- `detection_interval`: How often to run detection (default: 60 seconds)
- `anomaly_threshold`: Percentage of data points considered anomalies (default: 10%)
- `feature_columns`: Features used for ML analysis

### Alerting

Configure alerts in `anomaly/alert_handler.py`:

- Webhook URLs for Slack/Discord notifications
- Email configuration
- Alert severity thresholds

## Monitoring

### Grafana Dashboard

The dashboard includes:
- Anomaly detection overview
- Anomaly type distribution
- Timeline of recent anomalies
- Detailed anomaly table
- Response time analysis
- Status code distribution

### Log Analysis

View anomaly detection logs:
```bash
docker-compose logs -f anomaly-detector
```

## Anomaly Types Detected

1. **Response Time Anomalies**: Unusually slow or fast API responses
2. **Status Code Anomalies**: Unexpected HTTP status codes
3. **Behavioral Anomalies**: Unusual patterns in request features
4. **Suspicious Activity**: Pre-defined suspicious patterns

## Customization

### Adding New Features

To add new features for anomaly detection:

1. Update `feature_columns` in `LogAnomalyDetector.__init__()`
2. Modify `extract_features()` to include new feature extraction
3. Add new ML models if needed

### Custom Anomaly Rules

Add custom rules in `detect_anomalies()`:

```python
# Example: Custom rule for high error rates
if df['status_code'].mean() > 400:
    # Flag as anomaly
    pass
```

## Troubleshooting

### Common Issues

1. **No anomalies detected**: 
   - Check if logs are being collected by Loki
   - Verify anomaly detector is running: `docker-compose ps`
   - Check logs: `docker-compose logs anomaly-detector`

2. **Too many false positives**:
   - Increase `anomaly_threshold` value
   - Adjust ML model parameters
   - Add more training data

3. **Missing logs in Grafana**:
   - Verify Promtail is collecting logs
   - Check Loki connectivity
   - Import the dashboard configuration

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export LOG_LEVEL=DEBUG
```

## Performance

- **Memory Usage**: ~100-200MB per container
- **CPU Usage**: Low, runs every 60 seconds
- **Storage**: Minimal, only stores recent logs in memory
- **Network**: Only communicates with Loki

## Security

- Runs as non-root user in container
- No external API calls
- All data stays within your infrastructure
- Configurable alerting without exposing sensitive data
