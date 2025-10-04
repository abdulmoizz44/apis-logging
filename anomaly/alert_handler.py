#!/usr/bin/env python3
"""
Simple alert handler for anomaly detection
Can be extended to send emails, Slack messages, etc.
"""

import json
import logging
import requests
import time
from datetime import datetime
from typing import Dict, List

class AlertHandler:
    def __init__(self, webhook_url=None, email_config=None):
        self.webhook_url = webhook_url
        self.email_config = email_config
        self.alert_history = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def send_alert(self, anomaly_data: Dict):
        """Send alert for detected anomaly"""
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "severity": self._determine_severity(anomaly_data),
            "anomaly_type": anomaly_data.get('type', 'unknown'),
            "anomaly_score": anomaly_data.get('score', 0),
            "message": f"Anomaly detected: {anomaly_data.get('type', 'unknown')}",
            "details": anomaly_data
        }
        
        # Log alert
        self.logger.warning(f"ALERT: {json.dumps(alert, indent=2)}")
        
        # Store in history
        self.alert_history.append(alert)
        
        # Send webhook if configured
        if self.webhook_url:
            self._send_webhook(alert)
        
        # Send email if configured
        if self.email_config:
            self._send_email(alert)
    
    def _determine_severity(self, anomaly_data: Dict) -> str:
        """Determine alert severity based on anomaly data"""
        score = anomaly_data.get('score', 0)
        anomaly_type = anomaly_data.get('type', '')
        
        if score > 0.8 or anomaly_type in ['response_time_anomaly', 'status_code_anomaly']:
            return "HIGH"
        elif score > 0.5:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _send_webhook(self, alert: Dict):
        """Send alert to webhook URL"""
        try:
            response = requests.post(
                self.webhook_url,
                json=alert,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            self.logger.info("Alert sent via webhook successfully")
        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {e}")
    
    def _send_email(self, alert: Dict):
        """Send alert via email (placeholder - implement with your email service)"""
        # This is a placeholder - implement with your preferred email service
        # (SendGrid, AWS SES, SMTP, etc.)
        self.logger.info(f"Email alert would be sent: {alert['message']}")
    
    def get_alert_summary(self, hours: int = 24) -> Dict:
        """Get summary of alerts in the last N hours"""
        cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
        
        recent_alerts = [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert['timestamp']).timestamp() > cutoff_time
        ]
        
        severity_counts = {}
        type_counts = {}
        
        for alert in recent_alerts:
            severity = alert['severity']
            anomaly_type = alert['anomaly_type']
            
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            type_counts[anomaly_type] = type_counts.get(anomaly_type, 0) + 1
        
        return {
            "total_alerts": len(recent_alerts),
            "severity_breakdown": severity_counts,
            "type_breakdown": type_counts,
            "time_range_hours": hours
        }

# Example usage
if __name__ == "__main__":
    # Initialize alert handler
    handler = AlertHandler(
        webhook_url="https://hooks.slack.com/your-webhook-url",  # Optional
        email_config={"smtp_server": "smtp.gmail.com"}  # Optional
    )
    
    # Example anomaly data
    sample_anomaly = {
        "timestamp": datetime.utcnow(),
        "type": "response_time_anomaly",
        "score": 0.85,
        "response_time": 5000.0,
        "raw_log": {"endpoint": "/api/suspicious", "status_code": 200}
    }
    
    # Send alert
    handler.send_alert(sample_anomaly)
    
    # Get summary
    summary = handler.get_alert_summary()
    print(f"Alert Summary: {json.dumps(summary, indent=2)}")
