from main import run_experiment, print_readings
import imufusion
import numpy as np
from visualization import plot_position_in_real_time


# 1. Setup Parameters
SAMPLE_RATE = 100  # Hz
ZUPT_THRESHOLD = 0.04  # Sensitivity for detecting "static" state
GYRO_THRESHOLD = 5.0  # Sensitivity for detecting "static" state (degrees per second)
G_CONSTANT = 9.80665  # Conversion factor from m/s^2 to g

# 2. Initialize AHRS and State
ahrs = imufusion.Ahrs()
velocity = np.zeros(3)
position = np.zeros(3)
previous_time = 0

def track_step(gyro, accel, mag, time):
    global previous_time, velocity, position
    DT = time - previous_time
    previous_time = time

    # Update Orientation (9-axis AHRS)
    ahrs.update(gyro, accel, mag, DT)
    
    # Get Linear Acceleration in the Earth Frame (removes gravity)
    # This gives us the movement acceleration regardless of sensor tilt
    earth_accel = ahrs.earth_acceleration * G_CONSTANT  # Convert to m/s^2
    
    # 3. ZUPT Drift Correction Logic
    # If total acceleration change is very low, we assume the sensor is still
    is_static = np.linalg.norm(gyro) < GYRO_THRESHOLD and abs(np.linalg.norm(accel) - 1.0) < ZUPT_THRESHOLD
    
    if is_static:
        velocity = np.zeros(3)  # Reset velocity to STOP the drift
    else:
        # Integrate acceleration to get velocity: v = v + a*dt
        velocity += earth_accel * DT
        
    # Integrate velocity to get position: p = p + v*dt
    position += velocity * 0.1 * DT
    
    return position.copy(), velocity.copy(), is_static


def drift_correction(readings):
    gyrX = readings['buffer']['gyrX']['buffer'][0]
    gyrY = readings['buffer']['gyrY']['buffer'][0]
    gyrZ = readings['buffer']['gyrZ']['buffer'][0]
    accX = readings['buffer']['accX']['buffer'][0] 
    accY = readings['buffer']['accY']['buffer'][0] 
    accZ = readings['buffer']['accZ']['buffer'][0] 
    magX = readings['buffer']['magX']['buffer'][0]
    magY = readings['buffer']['magY']['buffer'][0]
    magZ = readings['buffer']['magZ']['buffer'][0]
    
    time = readings['buffer']['acc_time']['buffer'][0]

    if gyrX and gyrY and gyrZ and accX and accY and accZ and magX and magY and magZ and time:
        gyro = np.array([gyrX, gyrY, gyrZ]) * 57.29578 
        accel = np.array([accX, accY, accZ]) / G_CONSTANT
        mag = np.array([magX, magY, magZ])
        position, velocity, is_static = track_step(gyro, accel, mag, time)
        
        print(f"Position: {position}, Velocity: {velocity}, Static: {is_static}")
        plot_position_in_real_time(position)



if __name__ == "__main__":
    run_experiment(drift_correction)





