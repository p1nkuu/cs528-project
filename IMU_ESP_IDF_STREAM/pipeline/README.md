# IMU Gesture Recognition Pipeline

This folder contains a complete pipeline for collecting IMU data (accelerometer and gyroscope) via a serial stream (e.g., from an ESP32), training a 1D-CNN using TensorFlow/Keras, and running real-time inference on live data.

## Requirements & Setup

Before running the scripts, make sure you have the required dependencies installed:

```bash
pip install -r pipeline/requirements.txt
```

**Note:** The scripts assume your ESP32 is outputting data at 115200 baud with lines formatted like:
`AX:0.123 AY:-0.456 AZ:9.789 | GX:1.23 GY:-0.45 GZ:0.67 | T:25.30 C`

---

## Step 1: Data Collection (`collect_data.py`)

This script extracts data directly from the serial port and records 2-second windows (100 samples at 50Hz) whenever you press the `Enter` key.

- Connect your ESP32.
- Run the script:
  ```bash
  python pipeline/collect_data.py
  ```
- Type the name of the gesture you want to record (e.g., `Left`, `Forward`, `Idle`) and press Enter.
- **Tip for fast recording:** Once a label is set, just hit `Enter` to record another 2-second clip of the same gesture.
- Type `q` to quit.

The collected data will be appended to `pipeline/dataset.csv`. Ensure you have balanced data among all expected gesture classes!

---

## Step 2: Model Training (`train_model.py`)

Once you have recorded sufficient samples (windows) in `dataset.csv`, use this script to train your 1D-CNN. 

The network architecture includes two Conv1D layers (for spatial-temporal feature extraction), Max Pooling, and a Dense layer using softmax to classify between 7 distinct gestures (`Left`, `Right`, `Up`, `Down`, `Forward`, `Backward`, `Idle`).

- Run the training script:
  ```bash
  python pipeline/train_model.py
  ```
- This will load the CSV, group it by window ID, standardize it, one-hot encode the labels, split the data (80% Train / 20% Test), and train the model for 30 epochs.
- When finished, it evaluates the final accuracy and saves the trained Keras model to `pipeline/gesture_model.h5`.

---

## Step 3: Real-Time Inference (`inference.py`)

With `gesture_model.h5` created, you can execute real-time gesture recognition directly from the live streams using a threaded sliding window approach.

- Run the inference script:
  ```bash
  python pipeline/inference.py
  ```
- The script constantly buffers 2 seconds (100 samples) of live data in the background.
- Every `0.5` seconds, it standardizes the current buffer, feeds it into the trained model, and retrieves a sequence likelihood.
- If the identified gesture confidence is over `80%` (0.8 threshold) and the prediction isn't `Idle`, it prints the respective gesture to your console.
