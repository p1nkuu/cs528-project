import serial
import pygame
import re 
import math

# --- Configuration ---
SERIAL_PORT = 'COM4' # CHANGE TO SERIAL PORT OF YOUR ESP32
BAUD_RATE = 115200
WIDTH, HEIGHT = 1000, 800 # size of canvas

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("IMU Canvas")
screen.fill((255, 255, 255))

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    print(f"Connected to {SERIAL_PORT}")
except Exception as e:
    print(f"Error: {e}")
    exit()

px, py = WIDTH // 2, HEIGHT // 2
last_pos = [px, py]
running = True
vx, vy = 0, 0        

# orientation states
roll, pitch = 0, 0
p = 0.1

while running:
    dt = 1 / 115200 #assumes 100Hz update rate from the ESP32, might have to adjust

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            screen.fill((255, 255, 255))

    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        
        # extracts numbers from the serial moniter
        match_ax = re.search(r"AX:([-+]?\d*\.\d+|\d+)", line)
        match_ay = re.search(r"AY:([-+]?\d*\.\d+|\d+)", line)
        match_az = re.search(r"AZ:([-+]?\d*\.\d+|\d+)", line) 
        match_gx = re.search(r"GX:([-+]?\d*\.\d+|\d+)", line)
        match_gy = re.search(r"GY:([-+]?\d*\.\d+|\d+)", line)

        if match_ax and match_ay and match_az and match_gx and match_gy:
            ax = float(match_ax.group(1))
            ay = float(match_ay.group(1))
            az = float(match_az.group(1))
            gx = float(match_gx.group(1))
            gy = float(match_gy.group(1))

            #reduce sensitivity by ignoring small movement
            if abs(ax) < 0.4: ax = 0
            if abs(ay) < 0.4: ay = 0

            accel_roll = math.atan2(ay, az)
            accel_pitch = math.atan2(-ax, math.sqrt(ay**2 + az**2))

            roll = p * accel_roll + (1 - p) * (roll + gx * dt)
            pitch = p * accel_pitch + (1 - p) * (pitch + gy * dt)

            cos_r, sin_r = math.cos(roll), math.sin(roll)
            cos_p, sin_p = math.cos(pitch), math.sin(pitch)

            ax_w = ax * cos_p + az * sin_p
            ay_w = ax * sin_r * sin_p + ay * cos_r - az * sin_r * cos_p
            az_w = -ax * cos_r * sin_p + ay * sin_r + az * cos_r * cos_p

            az_w -= 9.81 

            # update coordinates (multiplied by 5 to see movement)
            px += ay*5
            py += ax*5

            # keep the pen on screen
            px = max(0, min(WIDTH, px))
            py = max(0, min(HEIGHT, py))

            new_pos = [int(px), int(py)]
            
            #integration
            vx += ax_w * dt * 0.95
            vy += ay_w * dt * 0.95

            px += vx * 100
            py -= vy * 100

            px = max(0, min(WIDTH, px))
            py = max(0, min(HEIGHT, py))

            new_pos = [int(px), int(py)]

            pygame.draw.line(screen, (0, 0, 0), last_pos, new_pos, 3)
            last_pos = new_pos

            

    pygame.display.flip()

ser.close()
pygame.quit()