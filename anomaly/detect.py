import time
import requests
import numpy as np
from pyod.models.iforest import IForest

PROMETHEUS = "http://prometheus:9090/api/v1/query"
PUSHGATEWAY = "http://pushgateway:9091/metrics/job/anomaly"
QUERY = 'rate(http_requests_total[1m])'   # you can change to any metric
INTERVAL = 60  # seconds

while True:
    try:
        # 1️⃣ Query Prometheus for the last minute of data
        r = requests.get(f"{PROMETHEUS}?query={QUERY}")
        result = r.json()['data']['result']

        # 2️⃣ Flatten numeric values
        values = []
        for item in result:
            try:
                val = float(item['value'][1])
                values.append(val)
            except Exception:
                pass

        if len(values) > 5:
            # 3️⃣ Train IsolationForest on historical pattern
            X = np.array(values).reshape(-1, 1)
            model = IForest(contamination=0.1)
            model.fit(X)
            score = model.decision_function(X)[-1]  # latest sample

            # 4️⃣ Push anomaly score to Prometheus Pushgateway
            metric = f"anomaly_score {score}\n"
            requests.post(PUSHGATEWAY, data=metric)
            print(f"[OK] anomaly_score={score:.4f}")
        else:
            print("[WARN] not enough data yet")

    except Exception as e:
        print("[ERROR]", e)

    time.sleep(INTERVAL)
