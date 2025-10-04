import json
import logging
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM
from collections import deque
import threading
import schedule
import warnings
warnings.filterwarnings('ignore')

class LogAnomalyDetector:
    def __init__(self, loki_url="http://loki:3100", detection_interval=60):
        self.loki_url = loki_url
        self.detection_interval = detection_interval
        self.log_buffer = deque(maxlen=1000)  # Keep last 1000 logs
        self.anomaly_threshold = 0.05  # 5% of data points as anomalies (less sensitive)
        self.models = {}
        self.scalers = {}
        self.feature_columns = [
            'response_time_ms', 'status_code', 'hour', 'minute', 
            'day_of_week', 'endpoint_length', 'user_agent_length'
        ]
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize models
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize ML models for different anomaly types"""
        # Isolation Forest for general anomalies
        self.models['isolation_forest'] = IsolationForest(
            contamination=self.anomaly_threshold,
            random_state=42,
            n_estimators=200,  # More trees for better accuracy
            max_samples=0.8    # Use 80% of data for training
        )
        
        # One-Class SVM for response time anomalies
        self.models['response_time_svm'] = OneClassSVM(
            nu=self.anomaly_threshold,
            kernel='rbf',
            gamma='auto'  # Better gamma selection
        )
        
        # One-Class SVM for status code anomalies
        self.models['status_code_svm'] = OneClassSVM(
            nu=self.anomaly_threshold,
            kernel='rbf',
            gamma='auto'  # Better gamma selection
        )
        
        # Initialize scalers
        for model_name in self.models:
            self.scalers[model_name] = StandardScaler()
    
    def fetch_logs_from_loki(self, minutes_back=5):
        """Fetch recent logs from Loki"""
        try:
            # Calculate time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=minutes_back)
            
            # Convert to nanoseconds (Loki uses nanoseconds)
            start_ns = int(start_time.timestamp() * 1000000000)
            end_ns = int(end_time.timestamp() * 1000000000)
            
            # Query Loki for logs
            query_url = f"{self.loki_url}/loki/api/v1/query_range"
            params = {
                'query': '{container="app"}',  # Adjust based on your container name
                'start': start_ns,
                'end': end_ns,
                'limit': 1000
            }
            
            response = requests.get(query_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logs = []
            
            if 'data' in data and 'result' in data['data']:
                for stream in data['data']['result']:
                    if 'values' in stream:
                        for timestamp, log_line in stream['values']:
                            try:
                                # Parse JSON log
                                log_entry = json.loads(log_line)
                                logs.append(log_entry)
                            except json.JSONDecodeError:
                                continue
            
            return logs
            
        except Exception as e:
            self.logger.error(f"Error fetching logs from Loki: {e}")
            return []
    
    def extract_features(self, logs):
        """Extract features from logs for ML analysis"""
        if not logs:
            return pd.DataFrame()
        
        features = []
        
        for log in logs:
            try:
                # Extract timestamp - handle empty timestamps and different formats
                timestamp_str = log.get('timestamp', '')
                if timestamp_str and timestamp_str.strip():
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    except ValueError:
                        # Try parsing with different format or use current time
                        try:
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                        except ValueError:
                            timestamp = datetime.utcnow()
                else:
                    # Use current time if no timestamp
                    timestamp = datetime.utcnow()
                
                # Extract features
                feature_row = {
                    'response_time_ms': float(log.get('response_time_ms', 0)),
                    'status_code': int(log.get('status_code', 200)),
                    'hour': timestamp.hour,
                    'minute': timestamp.minute,
                    'day_of_week': timestamp.weekday(),
                    'endpoint_length': len(log.get('endpoint', '')),
                    'user_agent_length': len(log.get('user_agent', '')),
                    'timestamp': timestamp,
                    'raw_log': log
                }
                
                # Add additional features if available
                if 'anomaly_score' in log:
                    feature_row['anomaly_score'] = float(log['anomaly_score'])
                else:
                    feature_row['anomaly_score'] = 0.0
                
                if 'suspicious_behavior' in log:
                    feature_row['suspicious_behavior'] = 1 if log['suspicious_behavior'] else 0
                else:
                    feature_row['suspicious_behavior'] = 0
                
                features.append(feature_row)
                
            except Exception as e:
                self.logger.warning(f"Error extracting features from log: {e}")
                continue
        
        return pd.DataFrame(features)
    
    def detect_anomalies(self, df):
        """Detect anomalies - only flag /api/suspicious endpoint as anomaly"""
        if len(df) < 5:  # Need minimum data
            self.logger.info(f"Not enough data for anomaly detection: {len(df)} logs (need 5+)")
            return []
        
        anomalies = []
        
        try:
            # Rule-based detection: Only /api/suspicious is considered anomalous
            for i, row in df.iterrows():
                raw_log = row['raw_log']
                endpoint = raw_log.get('endpoint', '')
                
                # Check if this is the suspicious endpoint
                if '/api/suspicious' in endpoint:
                    # Calculate anomaly score based on suspicious indicators
                    anomaly_score = 0.0
                    anomaly_reasons = []
                    
                    # Check for suspicious behavior flag
                    if raw_log.get('suspicious_behavior', False):
                        anomaly_score += 0.4
                        anomaly_reasons.append("suspicious_behavior_flag")
                    
                    # Check for unusual pattern flag
                    if raw_log.get('unusual_pattern', False):
                        anomaly_score += 0.3
                        anomaly_reasons.append("unusual_pattern_flag")
                    
                    # Check for high pre-calculated anomaly score
                    if raw_log.get('anomaly_score', 0) > 0.7:
                        anomaly_score += 0.3
                        anomaly_reasons.append(f"high_anomaly_score_{raw_log.get('anomaly_score', 0):.2f}")
                    
                    # Check for very slow response time (>2 seconds)
                    response_time = raw_log.get('response_time_ms', 0)
                    if response_time > 2000:
                        anomaly_score += 0.2
                        anomaly_reasons.append(f"slow_response_{response_time:.0f}ms")
                    
                    # Check for unusual response size
                    response_size = raw_log.get('response_size', 0)
                    if response_size > 1000:  # Large response
                        anomaly_score += 0.1
                        anomaly_reasons.append(f"large_response_{response_size}bytes")
                    
                    # Only flag if we have strong indicators
                    if anomaly_score > 0.5:
                        anomaly = {
                            'timestamp': row['timestamp'],
                            'type': 'suspicious_endpoint_anomaly',
                            'score': anomaly_score,
                            'endpoint': endpoint,
                            'reasons': anomaly_reasons,
                            'raw_log': raw_log
                        }
                        anomalies.append(anomaly)
                        self.logger.warning(f"SUSPICIOUS ENDPOINT DETECTED: {endpoint} - Reasons: {', '.join(anomaly_reasons)}")
            
            # Also check for other truly suspicious patterns in any endpoint
            for i, row in df.iterrows():
                raw_log = row['raw_log']
                endpoint = raw_log.get('endpoint', '')
                
                # Skip if already flagged as suspicious endpoint
                if '/api/suspicious' in endpoint:
                    continue
                
                # Check for very slow responses in normal endpoints (>5 seconds)
                response_time = raw_log.get('response_time_ms', 0)
                if response_time > 5000:  # 5 seconds
                    anomaly = {
                        'timestamp': row['timestamp'],
                        'type': 'performance_anomaly',
                        'score': 0.8,
                        'endpoint': endpoint,
                        'reasons': [f"extremely_slow_response_{response_time:.0f}ms"],
                        'raw_log': raw_log
                    }
                    anomalies.append(anomaly)
                    self.logger.warning(f"PERFORMANCE ANOMALY: {endpoint} - {response_time:.0f}ms response time")
                
                # Check for error status codes in normal endpoints
                status_code = raw_log.get('status_code', 200)
                if status_code >= 500:  # Server errors
                    anomaly = {
                        'timestamp': row['timestamp'],
                        'type': 'error_anomaly',
                        'score': 0.9,
                        'endpoint': endpoint,
                        'reasons': [f"server_error_{status_code}"],
                        'raw_log': raw_log
                    }
                    anomalies.append(anomaly)
                    self.logger.warning(f"ERROR ANOMALY: {endpoint} - Status {status_code}")
            
        except Exception as e:
            self.logger.error(f"Error in anomaly detection: {e}")
        
        return anomalies
    
    def process_anomalies(self, anomalies):
        """Process and alert on detected anomalies"""
        for anomaly in anomalies:
            self.logger.warning(f"ANOMALY DETECTED: {anomaly['type']} at {anomaly['timestamp']}")
            self.logger.warning(f"Anomaly details: {json.dumps(anomaly, default=str, indent=2)}")
            
            # Send alert to Loki for Grafana visualization
            self._send_anomaly_alert(anomaly)
    
    def _send_anomaly_alert(self, anomaly):
        """Send anomaly alert to Loki for visualization"""
        try:
            alert_data = {
                "timestamp": anomaly['timestamp'].isoformat(),
                "level": "WARNING",
                "message": f"Anomaly detected: {anomaly['type']}",
                "anomaly_type": anomaly['type'],
                "anomaly_score": anomaly['score'],
                "service": "anomaly_detector",
                "raw_log": anomaly['raw_log']
            }
            
            # Send to Loki
            loki_push_url = f"{self.loki_url}/loki/api/v1/push"
            payload = {
                "streams": [{
                    "stream": {"service": "anomaly_detector", "level": "WARNING"},
                    "values": [[str(int(anomaly['timestamp'].timestamp() * 1000000000)), json.dumps(alert_data)]]
                }]
            }
            
            response = requests.post(loki_push_url, json=payload, timeout=5)
            response.raise_for_status()
            
        except Exception as e:
            self.logger.error(f"Error sending anomaly alert: {e}")
    
    def run_detection_cycle(self):
        """Run one cycle of anomaly detection"""
        self.logger.info("Starting anomaly detection cycle...")
        
        # Fetch recent logs
        logs = self.fetch_logs_from_loki(minutes_back=5)
        self.logger.info(f"Fetched {len(logs)} logs for analysis")
        
        if not logs:
            return
        
        # Extract features
        df = self.extract_features(logs)
        if df.empty:
            self.logger.warning("No valid logs found for analysis")
            return
        
        # Detect anomalies
        anomalies = self.detect_anomalies(df)
        
        if anomalies:
            self.logger.warning(f"Detected {len(anomalies)} anomalies")
            self.process_anomalies(anomalies)
        else:
            self.logger.info("No anomalies detected")
    
    def start_monitoring(self):
        """Start continuous monitoring"""
        self.logger.info("Starting anomaly detection monitoring...")
        
        # Schedule detection every minute
        schedule.every(self.detection_interval).seconds.do(self.run_detection_cycle)
        
        # Run initial detection
        self.run_detection_cycle()
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    detector = LogAnomalyDetector()
    detector.start_monitoring()
