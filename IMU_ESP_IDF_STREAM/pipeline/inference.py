import time
import argparse
import re
import os
import threading
from collections import deque
import numpy as np
import serial
import serial.tools.list_ports
import tensorflow as tf
import joblib

# Configuration
BAUD_RATE = 115200
WINDOW_SIZE = 100  # 2 seconds of data at 50Hz
INFERENCE_INTERVAL = 0.5  # Run inference every 0.5 seconds
CONFIDENCE_THRESHOLD = 0.8
MODEL_FILE = "gesture_model.h5"
SCALER_FILE = "scaler.pkl"

EXPECTED_CLASSES = ['Left', 'Right', 'Up', 'Down', 'Forward', 'Backward', 'Idle']

# Regex that matches the streamed IMU output
LINE_RE = re.compile(
    r"AX:(?P<ax>[-\d.]+)\s+AY:(?P<ay>[-\d.]+)\s+AZ:(?P<az>[-\d.]+)"
    r".*?"
    r"GX:(?P<gx>[-\d.]+)\s+GY:(?P<gy>[-\d.]+)\s+GZ:(?P<gz>[-\d.]+)"
    r".*?"
    r"T:(?P<t>[-\d.]+)"
)

# Global buffer keeping the last exactly 100 valid samples
# deque maxlen automatically drops the oldest item when full
data_buffer = deque(maxlen=WINDOW_SIZE)

def find_port():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if "USB" in p.description or "Serial" in p.description or "UART" in p.description:
            return p.device
    if ports:
        return ports[0].device
    return None

def serial_reader_thread(port, baud):
    """
    Background thread to continually read from the serial port and append to the deque.
    """
    try:
        ser = serial.Serial(port, baud, timeout=1)
        print(f"[Thread] Connected to {port} at {baud} baud. Listening for IMU data...")
        
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                continue
            
            match = LINE_RE.search(line)
            if match:
                group = match.groupdict()
                row = [
                    float(group["ax"]), float(group["ay"]), float(group["az"]),
                    float(group["gx"]), float(group["gy"]), float(group["gz"])
                ]
                data_buffer.append(row)
                
    except Exception as e:
        print(f"[Thread] Serial error: {e}")
        os._exit(1)

def main():
    parser = argparse.ArgumentParser(description="Real-time IMU Gesture Inference")
    parser.add_argument("--port", type=str, help="Serial port of the ESP32")
    parser.add_argument("--baud", type=int, default=BAUD_RATE, help="Baud rate (default 115200)")
    args = parser.parse_args()

    port = args.port or find_port()
    if not port:
        print("Error: Could not automatically detect a serial port. Please specify with --port.")
        return

    # 1. Load the model and scaler
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, MODEL_FILE)
    scaler_path = os.path.join(script_dir, SCALER_FILE)
    
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}. Train the model first.")
        return
    if not os.path.exists(scaler_path):
        print(f"Error: Scaler not found at {scaler_path}. Train the model first.")
        return
        
    print("Loading model and scaler...")
    model = tf.keras.models.load_model(model_path)
    scaler = joblib.load(scaler_path)
    print("Model and scaler loaded successfully.")

    # 2. Start the serial reading thread
    reader = threading.Thread(target=serial_reader_thread, args=(port, args.baud), daemon=True)
    reader.start()

    # Wait for the buffer to fill up initially before we start predicting
    print(f"Waiting for buffer to fill ({WINDOW_SIZE} samples)...")
    while len(data_buffer) < WINDOW_SIZE:
        time.sleep(0.1)

    print("\n--- Starting Real-Time Inference ---")
    print(f"Interval: Every {INFERENCE_INTERVAL}s. Threshold: {CONFIDENCE_THRESHOLD * 100}%")

    try:
        while True:
            start_time = time.time()
            
            # Create a localized snapshot of the buffer so thread modification doesn't cause race conditions
            current_window = list(data_buffer)
            
            if len(current_window) == WINDOW_SIZE:
                # Convert to numpy array: shape (100, 6)
                X = np.array(current_window)
                
                # Normalize using the pre-trained scaler
                X_scaled = scaler.transform(X)
                
                # Model expects batch dimension: shape (1, 100, 6)
                X_input = np.expand_dims(X_scaled, axis=0)
                
                # Run inference
                predictions = model.predict(X_input, verbose=0)[0]
                
                # Get the class with highest probability
                pred_class_idx = np.argmax(predictions)
                confidence = predictions[pred_class_idx]
                predicted_label = EXPECTED_CLASSES[pred_class_idx]
                
                # Only output if confidence is high and it isn't just idling
                if confidence >= CONFIDENCE_THRESHOLD:
                    print(f"GESTURE DETECTED: {predicted_label} ({confidence:.2f} confidence)")
                else:
                    # Optional: uncomment if you want to see when it fails the threshold
                    pass 

            # Sleep enough to maintain the slide interval
            elapsed = time.time() - start_time
            sleep_time = max(0, INFERENCE_INTERVAL - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nInference stopped by user.")

if __name__ == "__main__":
    main()