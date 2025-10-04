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
        self.anomaly_threshold = 0.1  # 10% of data points as anomalies
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
            n_estimators=100
        )
        
        # One-Class SVM for response time anomalies
        self.models['response_time_svm'] = OneClassSVM(
            nu=self.anomaly_threshold,
            kernel='rbf',
            gamma='scale'
        )
        
        # One-Class SVM for status code anomalies
        self.models['status_code_svm'] = OneClassSVM(
            nu=self.anomaly_threshold,
            kernel='rbf',
            gamma='scale'
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
                # Extract timestamp
                timestamp = datetime.fromisoformat(log.get('timestamp', '').replace('Z', '+00:00'))
                
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
        """Detect anomalies using multiple ML models"""
        if len(df) < 10:  # Need minimum data for training
            return []
        
        anomalies = []
        
        try:
            # Prepare features
            X = df[self.feature_columns].fillna(0)
            
            # General anomaly detection with Isolation Forest
            if len(X) >= 10:
                X_scaled = self.scalers['isolation_forest'].fit_transform(X)
                isolation_predictions = self.models['isolation_forest'].fit_predict(X_scaled)
                
                for i, prediction in enumerate(isolation_predictions):
                    if prediction == -1:  # Anomaly detected
                        anomaly = {
                            'timestamp': df.iloc[i]['timestamp'],
                            'type': 'isolation_forest',
                            'score': abs(self.models['isolation_forest'].decision_function([X_scaled[i]])[0]),
                            'features': X.iloc[i].to_dict(),
                            'raw_log': df.iloc[i]['raw_log']
                        }
                        anomalies.append(anomaly)
            
            # Response time anomaly detection
            if 'response_time_ms' in df.columns and len(df) >= 10:
                response_times = df[['response_time_ms']].values
                response_times_scaled = self.scalers['response_time_svm'].fit_transform(response_times)
                response_predictions = self.models['response_time_svm'].fit_predict(response_times_scaled)
                
                for i, prediction in enumerate(response_predictions):
                    if prediction == -1:
                        anomaly = {
                            'timestamp': df.iloc[i]['timestamp'],
                            'type': 'response_time_anomaly',
                            'score': abs(self.models['response_time_svm'].decision_function([response_times_scaled[i]])[0]),
                            'response_time': df.iloc[i]['response_time_ms'],
                            'raw_log': df.iloc[i]['raw_log']
                        }
                        anomalies.append(anomaly)
            
            # Status code anomaly detection
            if 'status_code' in df.columns and len(df) >= 10:
                status_codes = df[['status_code']].values
                status_codes_scaled = self.scalers['status_code_svm'].fit_transform(status_codes)
                status_predictions = self.models['status_code_svm'].fit_predict(status_codes_scaled)
                
                for i, prediction in enumerate(status_predictions):
                    if prediction == -1:
                        anomaly = {
                            'timestamp': df.iloc[i]['timestamp'],
                            'type': 'status_code_anomaly',
                            'score': abs(self.models['status_code_svm'].decision_function([status_codes_scaled[i]])[0]),
                            'status_code': df.iloc[i]['status_code'],
                            'raw_log': df.iloc[i]['raw_log']
                        }
                        anomalies.append(anomaly)
            
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
