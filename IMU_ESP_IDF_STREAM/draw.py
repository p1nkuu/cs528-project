import serial
import pygame
import re
import math

# --- Configuration ---
SERIAL_PORT = 'COM5'
BAUD_RATE = 115200
WIDTH, HEIGHT = 1000, 800

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("IMU CANVAS - Regex Mode")
screen.fill((255, 255, 255))

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    print(f"Connected to {SERIAL_PORT}")
except Exception as e:
    print(f"Error: {e}")
    exit()

px, py = WIDTH // 2, HEIGHT // 2
last_pos = [px, py]
vx, vy = 0, 0

# orientation states
roll, pitch = 0, 0
p = 0.1

running = True

scale = 200     # scale position movement
friction = 0.95     

while running:
    dt = 1 / 100

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_c:
                screen.fill((255, 255, 255))
            if event.key == pygame.K_r:
                vx, vy = 0, 0
                px, py = WIDTH // 2, HEIGHT // 2

    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()

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

            # orientation estimation
            # equations based on https://medium.com/@alikhuzaifaali1129/complementary-filter-on-accelerometer-and-gyroscope-b6f9aa4e49ca
            accel_roll = math.atan2(ay, az)
            accel_pitch = math.atan2(-ax, math.sqrt(ay**2 + az**2))

            roll = p * accel_roll + (1 - p) * (roll + gx * dt)
            pitch = p * accel_pitch + (1 - p) * (pitch + gy * dt)

            # "Transform the acceleration measurements (taken in a non inertial reference frame: the one attached to your sensor) 
            # to the inertial reference frame using the rotation transformation obtained with orientation estimation."
            cos_r, sin_r = math.cos(roll), math.sin(roll)
            cos_p, sin_p = math.cos(pitch), math.sin(pitch)

            ax_w = ax * cos_p + az * sin_p
            ay_w = ax * sin_r * sin_p + ay * cos_r - az * sin_r * cos_p
            az_w = -ax * cos_r * sin_p + ay * sin_r + az * cos_r * cos_p

            # subtracting gravity
            az_w -= 9.81 

            # reduce sensitivity by ignoring small movement
            if abs(ax_w) < 0.05: ax_w = 0
            if abs(ay_w) < 0.05: ay_w = 0

            # integration to get velocity and position
            vx += ax_w * dt * friction
            vy += ay_w * dt * friction

            px += vx * scale
            py -= vy * scale

            px = max(0, min(WIDTH, px))
            py = max(0, min(HEIGHT, py))

            new_pos = [int(px), int(py)]

            pygame.draw.line(screen, (0, 0, 0), last_pos, new_pos, 3)
            last_pos = new_pos

    pygame.display.flip()

ser.close()
pygame.quit()