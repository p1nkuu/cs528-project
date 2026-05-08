import serial
import re
import csv
from datetime import datetime
import os

SERIAL_PORT = 'COM5' 
BAUD_RATE = 115200
OUTPUT_DIR = 'data/final/left'
FILE_PREFIX = 'left'
RECORD_DURATION = 0.5

os.makedirs(OUTPUT_DIR, exist_ok=True)

counter = 0
while True:
    filename = f"{FILE_PREFIX}_{counter:02d}.txt"
    output_file = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(output_file):
        break
    counter += 1

pattern = re.compile(
    r'AX:([-\d.]+)\s+AY:([-\d.]+)\s+AZ:([-\d.]+)\s+\|\s+'
    r'GX:([-\d.]+)\s+GY:([-\d.]+)\s+GZ:([-\d.]+)\s+\|\s+'
    r'T:([-\d.]+)'
)

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

with open(output_file, 'w', newline='') as csvfile:
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(['DeltaTime_s', 'AccelX', 'AccelY', 'AccelZ', 'GyroX', 'GyroY', 'GyroZ', 'Temp'])

    sample_count = 0
    start_time = None  

    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if not line:
            continue
            
        match = pattern.search(line)
        if match:
            ax, ay, az = match.group(1), match.group(2), match.group(3)
            gx, gy, gz = match.group(4), match.group(5), match.group(6)
            temp = match.group(7)

            current_time = datetime.now()
            if start_time is None:
                start_time = current_time
                delta_time = 0.0
            else:
                delta_time = (current_time - start_time).total_seconds()

            csv_writer.writerow([f'{delta_time:.6f}', ax, ay, az, gx, gy, gz, temp])
            sample_count += 1
            print(line)

            if delta_time >= RECORD_DURATION:
                break
