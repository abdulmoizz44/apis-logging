import time
import requests
import numpy as np
import json
from datetime import datetime, timedelta
from pyod.models.iforest import IForest

LOKI = "http://loki:3100/loki/api/v1/query_range"
LOKI_PUSH = "http://loki:3100/loki/api/v1/push"
INTERVAL = 60  # seconds

def query_loki_logs(start_time, end_time, query='{job="app"}'):
    """Query Loki for logs in the specified time range"""
    params = {
        'query': query,
        'start': start_time,
        'end': end_time,
        'limit': 1000
    }
    try:
        r = requests.get(LOKI, params=params)
        return r.json()
    except Exception as e:
        print(f"[ERROR] Loki query failed: {e}")
        return None

def extract_log_metrics(logs_data):
    """Extract metrics from Loki logs"""
    if not logs_data or 'data' not in logs_data:
        return []
    
    metrics = []
    for stream in logs_data['data'].get('result', []):
        for entry in stream.get('values', []):
            try:
                # Parse log entry timestamp and message
                timestamp = int(entry[0]) // 1000000000  # Convert nanoseconds to seconds
                log_line = entry[1]
                
                # Extract log level and basic metrics
                log_level = 'INFO'  # default
                if 'ERROR' in log_line.upper():
                    log_level = 'ERROR'
                elif 'WARN' in log_line.upper():
                    log_level = 'WARN'
                elif 'DEBUG' in log_line.upper():
                    log_level = 'DEBUG'
                
                # Count log volume and error rate
                metrics.append({
                    'timestamp': timestamp,
                    'level': log_level,
                    'is_error': log_level == 'ERROR',
                    'line_length': len(log_line)
                })
            except Exception as e:
                continue
    
    return metrics

def calculate_log_features(metrics):
    """Calculate features for anomaly detection"""
    if len(metrics) < 5:
        return None
    
    # Calculate time-based features
    timestamps = [m['timestamp'] for m in metrics]
    time_span = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 1
    
    # Log volume per minute
    log_volume = len(metrics) / max(time_span / 60, 1)
    
    # Error rate
    error_count = sum(1 for m in metrics if m['is_error'])
    error_rate = error_count / len(metrics) if metrics else 0
    
    # Average log line length
    avg_line_length = np.mean([m['line_length'] for m in metrics])
    
    # Log level distribution
    level_counts = {}
    for m in metrics:
        level = m['level']
        level_counts[level] = level_counts.get(level, 0) + 1
    
    # Calculate entropy of log levels (diversity measure)
    total_logs = len(metrics)
    entropy = 0
    for count in level_counts.values():
        p = count / total_logs
        if p > 0:
            entropy -= p * np.log2(p)
    
    return [log_volume, error_rate, avg_line_length, entropy]

def push_anomaly_to_loki(anomaly_score, timestamp):
    """Push anomaly detection result to Loki"""
    log_entry = {
        "streams": [{
            "stream": {
                "job": "anomaly-detector",
                "level": "INFO"
            },
            "values": [[
                str(timestamp * 1000000000),  # Convert to nanoseconds
                json.dumps({
                    "anomaly_score": anomaly_score,
                    "timestamp": timestamp,
                    "message": f"Anomaly detected with score: {anomaly_score:.4f}"
                })
            ]]
        }]
    }
    
    try:
        requests.post(LOKI_PUSH, 
                     headers={'Content-Type': 'application/json'},
                     data=json.dumps(log_entry))
    except Exception as e:
        print(f"[ERROR] Failed to push to Loki: {e}")

# Store historical features for training
historical_features = []

while True:
    try:
        # 1️⃣ Query Loki for logs from the last minute
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=1)
        
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        
        logs_data = query_loki_logs(start_ts, end_ts)
        if not logs_data:
            print("[WARN] No logs data received")
            time.sleep(INTERVAL)
            continue
        
        # 2️⃣ Extract metrics from logs
        metrics = extract_log_metrics(logs_data)
        if not metrics:
            print("[WARN] No metrics extracted from logs")
            time.sleep(INTERVAL)
            continue
        
        # 3️⃣ Calculate features for anomaly detection
        features = calculate_log_features(metrics)
        if features is None:
            print("[WARN] Not enough data for feature calculation")
            time.sleep(INTERVAL)
            continue
        
        # 4️⃣ Store features and train model
        historical_features.append(features)
        
        # Keep only last 100 samples for training
        if len(historical_features) > 100:
            historical_features = historical_features[-100:]
        
        if len(historical_features) > 10:
            # 5️⃣ Train IsolationForest on log patterns
            X = np.array(historical_features)
            model = IForest(contamination=0.1, random_state=42)
            model.fit(X)
            
            # 6️⃣ Calculate anomaly score for current features
            current_score = model.decision_function([features])[0]
            is_anomaly = model.predict([features])[0] == -1
            
            # 7️⃣ Push anomaly result to Loki
            push_anomaly_to_loki(current_score, end_ts)
            
            status = "ANOMALY" if is_anomaly else "NORMAL"
            print(f"[{status}] anomaly_score={current_score:.4f}, features={features}")
        else:
            print(f"[INFO] Collecting data... ({len(historical_features)}/10 samples)")

    except Exception as e:
        print(f"[ERROR] {e}")

    time.sleep(INTERVAL)
