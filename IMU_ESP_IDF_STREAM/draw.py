import serial
import pygame
import re 

# --- Configuration ---
SERIAL_PORT = 'COM4' # CHANGE TO SERIAL PORT OF YOUR ESP32
BAUD_RATE = 115200
WIDTH, HEIGHT = 1000, 800 # size of canvas

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("IMU Canvas - Regex Mode")
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



while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            screen.fill((255, 255, 255))

    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        
        # extracts numbers from the serial moniter
        match_y = re.search(r"AX:([-+]?\d*\.\d+|\d+)", line) #had to switch the X and Y because the axes were flipped for some reason
        match_x = re.search(r"AY:([-+]?\d*\.\d+|\d+)", line)

        if match_x and match_y:
            ax = float(match_x.group(1))
            ay = float(match_y.group(1))
            # not considering az for now because it is affected by gravity and neeeds a calibration step to be useful

            #reduce sensitivity by ignoring small movement
            if abs(ax) < 0.05: ax = 0
            if abs(ay) < 0.05: ay = 0


            # update coordinates (multiplied by 5 to see movement)
            px += ax * 5 
            py -= ay * 5 

            # keep the pen on screen
            px = max(0, min(WIDTH, px))
            py = max(0, min(HEIGHT, py))

            new_pos = [int(px), int(py)]
            
            pygame.draw.line(screen, (0, 0, 0), last_pos, new_pos, 3)
            last_pos = new_pos

    pygame.display.flip()

ser.close()
pygame.quit()