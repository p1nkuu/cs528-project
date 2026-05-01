# Shared configuration for the IMU Machine Learning Pipeline

# Data Collection & Windowing
SAMPLE_HZ = 100                 # Sampling frequency in Hz
WINDOW_DURATION_SEC = 1.0       # Duration of each gesture window in seconds
SAMPLES_PER_WINDOW = int(SAMPLE_HZ * WINDOW_DURATION_SEC)

# Serial Communication
BAUD_RATE = 115200

# Classes and Features
EXPECTED_CLASSES = ['Left', 'Right', 'Up', 'Down', 'Forward', 'Backward', 'Idle']
FEATURES = ['ax', 'ay', 'az', 'gx', 'gy', 'gz']

# File Paths
CSV_FILE = "dataset.csv"
MODEL_NAME = "gesture_model.h5"
SCALER_NAME = "scaler.pkl"
