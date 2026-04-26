import requests
import time

# 1. SET YOUR PHONE'S IP ADDRESS
# Replace with the URL shown at the bottom of your phone screen
PHYPHOX_URL = "http://172.31.206.75:8080" 


def control_phyphox(command):
    """Sends control commands: 'start', 'stop', or 'clear'"""
    try:
        requests.get(f"{PHYPHOX_URL}/control?cmd={command}")
    except requests.exceptions.RequestException as e:
        print(f"Command '{command}' failed: {e}")




def fetch_data():
    try:
        # 2. REQUEST SPECIFIC SENSOR BUFFERS
        # 'accX', 'accY', 'accZ' are standard for the Accelerometer experiment
        response = requests.get(f"{PHYPHOX_URL}/get?acc_time&accX&accY&accZ&linX&linY&linZ&gyrX&gyrY&gyrZ&magX&magY&magZ")
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Error: Server responded with status {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Connection failed: {e}")




def run_experiment(func=None):
    try:
        # PREPARE: Clear old data and start fresh
        control_phyphox("clear")
        time.sleep(0.2)
        control_phyphox("start")
        print("Experiment started. Press Ctrl+C to stop script AND experiment.")

        while True:
            time.sleep(0.1)
            readings = fetch_data()
            func(readings)

    except KeyboardInterrupt:
        print("\nStopping script...")

    finally:
        # 2. THE EXIT COMMAND
        # This block always runs, even if you press Ctrl+C
        print("Sending 'STOP' command to phyphox...")
        control_phyphox("stop")
        print("Done.")




def print_readings(readings):
    if readings:
        time = readings['buffer']['acc_time']['buffer'][0]
        x = readings['buffer']['accX']['buffer'][0]
        y = readings['buffer']['accY']['buffer'][0]
        z = readings['buffer']['accZ']['buffer'][0]
        linX = readings['buffer']['linX']['buffer'][0]
        linY = readings['buffer']['linY']['buffer'][0]
        linZ = readings['buffer']['linZ']['buffer'][0]
        gyrX = readings['buffer']['gyrX']['buffer'][0]
        gyrY = readings['buffer']['gyrY']['buffer'][0]
        gyrZ = readings['buffer']['gyrZ']['buffer'][0]
        magX = readings['buffer']['magX']['buffer'][0]
        magY = readings['buffer']['magY']['buffer'][0]
        magZ = readings['buffer']['magZ']['buffer'][0]
        

        if x and y and z and linX and linY and linZ and time:
            print(f"Time: {time:.3f} s | X: {x:+.3f} | Y: {y:+.3f} | Z: {z:+.3f} | Linear X: {linX:+.3f} | Linear Y: {linY:+.3f} | Linear Z: {linZ:+.3f} | Angular X: {gyrX:+.3f} | Angular Y: {gyrY:+.3f} | Angular Z: {gyrZ:+.3f} | Magnetic X: {magX:+.3f} | Magnetic Y: {magY:+.3f} | Magnetic Z: {magZ:+.3f} ")


if __name__ == "__main__":
    run_experiment(print_readings)