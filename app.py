import logging
import json
import random
import time
from datetime import datetime
from flask import Flask, request, jsonify
from pythonjsonlogger import jsonlogger

app = Flask(__name__)

# Configure JSON logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Normal endpoints data
users = [
    {"id": 1, "name": "John Doe", "email": "john@example.com", "role": "user"},
    {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "role": "admin"},
    {"id": 3, "name": "Bob Johnson", "email": "bob@example.com", "role": "user"}
]

products = [
    {"id": 1, "name": "Laptop", "price": 999.99, "category": "electronics"},
    {"id": 2, "name": "Mouse", "price": 29.99, "category": "electronics"},
    {"id": 3, "name": "Keyboard", "price": 79.99, "category": "electronics"}
]

orders = [
    {"id": 1, "user_id": 1, "product_id": 1, "quantity": 1, "total": 999.99, "status": "completed"},
    {"id": 2, "user_id": 2, "product_id": 2, "quantity": 2, "total": 59.98, "status": "pending"}
]

def log_request(endpoint, method, status_code, response_time, user_agent, ip_address, additional_data=None):
    """Log request with structured data for anomaly detection"""
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "response_time_ms": response_time,
        "user_agent": user_agent,
        "ip_address": ip_address,
        "request_id": f"req_{int(time.time() * 1000)}"
    }
    
    if additional_data:
        log_data.update(additional_data)
    
    logger.info("API Request", extra=log_data)

@app.route('/api/users', methods=['GET'])
def get_users():
    start_time = time.time()
    
    try:
        # Simulate normal processing time
        time.sleep(random.uniform(0.01, 0.05))
        
        response = jsonify({
            "success": True,
            "data": users,
            "count": len(users)
        })
        
        response_time = (time.time() - start_time) * 1000
        log_request(
            endpoint="/api/users",
            method="GET",
            status_code=200,
            response_time=response_time,
            user_agent=request.headers.get('User-Agent', 'Unknown'),
            ip_address=request.remote_addr,
            additional_data={"user_count": len(users)}
        )
        
        return response, 200
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        log_request(
            endpoint="/api/users",
            method="GET",
            status_code=500,
            response_time=response_time,
            user_agent=request.headers.get('User-Agent', 'Unknown'),
            ip_address=request.remote_addr,
            additional_data={"error": str(e)}
        )
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    start_time = time.time()
    
    try:
        # Simulate normal processing time
        time.sleep(random.uniform(0.01, 0.05))
        
        response = jsonify({
            "success": True,
            "data": products,
            "count": len(products)
        })
        
        response_time = (time.time() - start_time) * 1000
        log_request(
            endpoint="/api/products",
            method="GET",
            status_code=200,
            response_time=response_time,
            user_agent=request.headers.get('User-Agent', 'Unknown'),
            ip_address=request.remote_addr,
            additional_data={"product_count": len(products)}
        )
        
        return response, 200
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        log_request(
            endpoint="/api/products",
            method="GET",
            status_code=500,
            response_time=response_time,
            user_agent=request.headers.get('User-Agent', 'Unknown'),
            ip_address=request.remote_addr,
            additional_data={"error": str(e)}
        )
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    start_time = time.time()
    
    try:
        # Simulate normal processing time
        time.sleep(random.uniform(0.01, 0.05))
        
        response = jsonify({
            "success": True,
            "data": orders,
            "count": len(orders)
        })
        
        response_time = (time.time() - start_time) * 1000
        log_request(
            endpoint="/api/orders",
            method="GET",
            status_code=200,
            response_time=response_time,
            user_agent=request.headers.get('User-Agent', 'Unknown'),
            ip_address=request.remote_addr,
            additional_data={"order_count": len(orders)}
        )
        
        return response, 200
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        log_request(
            endpoint="/api/orders",
            method="GET",
            status_code=500,
            response_time=response_time,
            user_agent=request.headers.get('User-Agent', 'Unknown'),
            ip_address=request.remote_addr,
            additional_data={"error": str(e)}
        )
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route('/api/suspicious', methods=['GET', 'POST'])
def suspicious_endpoint():
    start_time = time.time()
    
    try:
        # Simulate suspicious behavior patterns
        suspicious_behaviors = [
            lambda: time.sleep(random.uniform(2, 5)),  # Very slow response
            lambda: random.choice([400, 401, 403, 500]),  # High error rate
            lambda: random.randint(1000, 10000),  # Unusual response size
            lambda: random.choice(['admin', 'root', 'test', 'hack']),  # Suspicious user agents
        ]
        
        behavior = random.choice(suspicious_behaviors)
        
        if callable(behavior):
            if behavior.__name__ == '<lambda>':
                # Handle different suspicious behaviors
                if random.random() < 0.3:  # 30% chance of slow response
                    time.sleep(random.uniform(2, 5))
                    status_code = 200
                elif random.random() < 0.4:  # 40% chance of error
                    status_code = random.choice([400, 401, 403, 500])
                else:  # 30% chance of unusual response
                    status_code = 200
            else:
                status_code = 200
        else:
            status_code = behavior
        
        # Generate suspicious response data
        suspicious_data = {
            "success": status_code == 200,
            "data": {
                "message": "This is a suspicious endpoint",
                "random_data": [random.randint(1, 1000) for _ in range(random.randint(50, 200))],
                "timestamp": datetime.utcnow().isoformat(),
                "suspicious_flag": True
            }
        }
        
        response_time = (time.time() - start_time) * 1000
        
        # Log with suspicious patterns
        log_request(
            endpoint="/api/suspicious",
            method=request.method,
            status_code=status_code,
            response_time=response_time,
            user_agent=request.headers.get('User-Agent', 'Unknown'),
            ip_address=request.remote_addr,
            additional_data={
                "suspicious_behavior": True,
                "response_size": len(json.dumps(suspicious_data)),
                "unusual_pattern": True,
                "anomaly_score": random.uniform(0.7, 1.0)
            }
        )
        
        return jsonify(suspicious_data), status_code
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        log_request(
            endpoint="/api/suspicious",
            method=request.method,
            status_code=500,
            response_time=response_time,
            user_agent=request.headers.get('User-Agent', 'Unknown'),
            ip_address=request.remote_addr,
            additional_data={
                "error": str(e),
                "suspicious_behavior": True,
                "anomaly_score": 1.0
            }
        )
        return jsonify({"success": False, "error": "Suspicious error occurred"}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200

if __name__ == '__main__':
    print("Starting Anomaly Detection Test Application...")
    print("Available endpoints:")
    print("  GET  /api/users      - Normal endpoint")
    print("  GET  /api/products   - Normal endpoint") 
    print("  GET  /api/orders     - Normal endpoint")
    print("  GET  /api/suspicious - Suspicious endpoint (generates anomalies)")
    print("  GET  /api/health     - Health check")
    print("\nLogs will be output in JSON format for anomaly detection analysis.")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
