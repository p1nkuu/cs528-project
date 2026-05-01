import time
import argparse
import re
import os
import pandas as pd
import serial
import serial.tools.list_ports

# Configuration
BAUD_RATE = 115200
SAMPLE_HZ = 100
SAMPLES_NEEDED = 100  # 2 seconds of data at 50Hz
CSV_FILE = "dataset.csv"
EXPECTED_CLASSES = ['Left', 'Right', 'Up', 'Down', 'Forward', 'Backward', 'Idle']

# Regex that matches the streamed IMU output from plot_imu.py
LINE_RE = re.compile(
    r"AX:(?P<ax>[-\d.]+)\s+AY:(?P<ay>[-\d.]+)\s+AZ:(?P<az>[-\d.]+)"
    r".*?"
    r"GX:(?P<gx>[-\d.]+)\s+GY:(?P<gy>[-\d.]+)\s+GZ:(?P<gz>[-\d.]+)"
    r".*?"
    r"T:(?P<t>[-\d.]+)"
)

def find_port():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if "USB" in p.description or "Serial" in p.description or "UART" in p.description:
            return p.device
    if ports:
        return ports[0].device
    return None

def main():
    parser = argparse.ArgumentParser(description="Collect IMU data for Machine Learning.")
    parser.add_argument("--port", type=str, help="Serial port of the ESP32")
    parser.add_argument("--baud", type=int, default=BAUD_RATE, help="Baud rate (default 115200)")
    parser.add_argument("--out", type=str, default=CSV_FILE, help="Output CSV file name")
    args = parser.parse_args()

    port = args.port or find_port()
    if not port:
        print("Error: Could not automatically detect a serial port. Please specify with --port.")
        return

    print(f"Connecting to {port} at {args.baud} baud...")
    try:
        ser = serial.Serial(port, args.baud, timeout=1)
    except Exception as e:
        print(f"Failed to open port {port}: {e}")
        return

    print("\n--- IMU Data Collection ---")
    current_label = "Idle"
    
    # Save the CSV file relative to this script inside the pipeline folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(script_dir, args.out)

    try:
        while True:
            print(f"\n---")
            print(f"Valid classes: {', '.join(EXPECTED_CLASSES)}")
            user_input = input(f"Current label is '{current_label}'.\nEnter new label, 'q' to quit, or press Enter to keep '{current_label}' and record: ").strip()
            
            if user_input.lower() == 'q':
                break
            elif user_input:
                match_class = next((c for c in EXPECTED_CLASSES if c.lower() == user_input.lower()), None)
                if match_class:
                    current_label = match_class
                else:
                    print(f"⚠️ Warning: '{user_input}' is not a valid class. Please choose from: {', '.join(EXPECTED_CLASSES)}")
                    continue
            
            print(f"Recording {SAMPLES_NEEDED} samples for label '{current_label}'...")
            
            window_id = int(time.time() * 1000) # Unique ID based on ms timestamp
            data = []
            
            # VERY IMPORTANT: Flush the serial buffer before recording
            # This ensures we get fresh data from the *start* of the keypress,
            # discarding any old data buffered by the OS.
            ser.reset_input_buffer()
            
            valid_samples = 0
            next_sample_time = time.time()
            
            while valid_samples < SAMPLES_NEEDED:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                
                match = LINE_RE.search(line)
                if match:
                    current_time = time.time()
                    
                    # Throttle collection to match exactly our expected SAMPLE_HZ
                    if current_time >= next_sample_time:
                        group = match.groupdict()
                        data.append({
                            "window_id": window_id,
                            "timestamp_ms": int(current_time * 1000),
                            "label": current_label,
                            "ax": float(group["ax"]),
                            "ay": float(group["ay"]),
                            "az": float(group["az"]),
                            "gx": float(group["gx"]),
                            "gy": float(group["gy"]),
                            "gz": float(group["gz"])
                        })
                        valid_samples += 1
                        
                        # Set target time for the next sample to maintain 50Hz exactly
                        next_sample_time += (1.0 / SAMPLE_HZ)
                        # If we fell significantly behind (e.g. PC lag, or slow serial), 
                        # reset next_sample_time to current interval to prevent burst reading
                        if current_time > next_sample_time:
                            next_sample_time = current_time + (1.0 / SAMPLE_HZ)
                        
                        # Print progress bar every 20 samples
                        if valid_samples % 20 == 0:
                            print(f"[{valid_samples}/{SAMPLES_NEEDED}] ...")

            # Convert to Pandas DataFrame
            df = pd.DataFrame(data)
            
            # Determine if we need to write headers (only if file doesn't exist)
            write_header = not os.path.exists(out_path)
            
            # Append DataFrame to CSV
            df.to_csv(out_path, mode='a', index=False, header=write_header)
            
            print(f"Successfully recorded 2 seconds of '{current_label}' data!")
            print(f"Saved {SAMPLES_NEEDED} rows to {out_path} (Window ID: {window_id})")

    except KeyboardInterrupt:
        print("\nCollection aborted by user.")
    finally:
        ser.close()
        print("Serial port closed.")

if __name__ == "__main__":
    main()
