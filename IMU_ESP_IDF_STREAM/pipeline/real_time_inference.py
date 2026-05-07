import serial
import re
import numpy as np
import joblib
import time
import requests
from collections import deque, Counter
from features import extract_features_from_array

SERIAL_PORT = 'COM4'
BAUD_RATE = 115200
WINDOW_SIZE = 100
OVERLAP = 99
VOTE_COUNT = 100
UI_SERVER_URL = "http://localhost:8000/predict"

def main():
    scaler = joblib.load('models/scaler.joblib')
    svm_model = joblib.load('models/classifier.joblib')

    pattern = re.compile(
        r'AX:([-\d.]+)\s+AY:([-\d.]+)\s+AZ:([-\d.]+)\s+\|\s+'
        r'GX:([-\d.]+)\s+GY:([-\d.]+)\s+GZ:([-\d.]+)\s+\|\s+'
        r'T:([-\d.]+)'
    )

    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    buffer = deque(maxlen=WINDOW_SIZE)
    prediction_history = deque(maxlen=VOTE_COUNT)

    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if not line:
            continue
            
        match = pattern.search(line)
        if match:
            ax, ay, az = float(match.group(1)), float(match.group(2)), float(match.group(3))
            gx, gy, gz = float(match.group(4)), float(match.group(5)), float(match.group(6))
            
            buffer.append([ax, ay, az, gx, gy, gz])

            if len(buffer) == WINDOW_SIZE:
                data_array = np.array(buffer)
                accel_std = np.mean(np.std(data_array[:, :3], axis=0))
                
                if accel_std > 0.1:
                    features = extract_features_from_array(data_array)
                    features_scaled = scaler.transform([features])
                    prediction = svm_model.predict(features_scaled)[0]
                    prediction_history.append(prediction)
                    
                    if len(prediction_history) == VOTE_COUNT:
                        most_common = Counter(prediction_history).most_common(1)[0][0]
                        print(f"[{time.strftime('%H:%M:%S')}] Detected Gesture: {most_common}")
                        
                        # Send to UI if running
                        try:
                            requests.post(UI_SERVER_URL, json={"action": str(most_common)}, timeout=0.1)
                        except requests.exceptions.RequestException:
                            pass # Silently ignore connection errors
                            
                        prediction_history.clear()
                else:
                    prediction_history.clear()
                
                for _ in range(WINDOW_SIZE - OVERLAP):
                    buffer.popleft()

if __name__ == '__main__':
    main()