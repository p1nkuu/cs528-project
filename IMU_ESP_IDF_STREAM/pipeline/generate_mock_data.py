import os
import time
import numpy as np
import pandas as pd

# Configuration
CSV_FILE = "dataset.csv"
SAMPLES_PER_WINDOW = 100
WINDOWS_PER_CLASS = 20  # How many 2-second windows to generate per class
EXPECTED_CLASSES = ['Left', 'Right', 'Up', 'Down', 'Forward', 'Backward', 'Idle']

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(script_dir, CSV_FILE)
    
    data = []
    base_time = int(time.time() * 1000)
    
    print(f"Generating mock data for {len(EXPECTED_CLASSES)} classes...")
    print(f"Each class will have {WINDOWS_PER_CLASS} windows ({WINDOWS_PER_CLASS * SAMPLES_PER_WINDOW} rows).")
    
    for class_idx, label in enumerate(EXPECTED_CLASSES):
        for w in range(WINDOWS_PER_CLASS):
            window_id = base_time + (class_idx * WINDOWS_PER_CLASS + w) * 2000 # 2 seconds apart
            
            # Generate 100 samples of random noise.
            # We add a distinct offset based on the class index so the neural network 
            # can actually find a pattern and achieve high accuracy during the test.
            ax = np.random.randn(SAMPLES_PER_WINDOW) * 0.5 + class_idx
            ay = np.random.randn(SAMPLES_PER_WINDOW) * 0.5 - class_idx
            az = np.random.randn(SAMPLES_PER_WINDOW) * 0.5 + (class_idx % 3)
            gx = np.random.randn(SAMPLES_PER_WINDOW) * 0.1 + (class_idx * 0.2)
            gy = np.random.randn(SAMPLES_PER_WINDOW) * 0.1 - (class_idx * 0.2)
            gz = np.random.randn(SAMPLES_PER_WINDOW) * 0.1
            
            for i in range(SAMPLES_PER_WINDOW):
                data.append({
                    "window_id": window_id,
                    "timestamp_ms": window_id + (i * 20), # Mock 50Hz (20ms step)
                    "label": label,
                    "ax": ax[i],
                    "ay": ay[i],
                    "az": az[i],
                    "gx": gx[i],
                    "gy": gy[i],
                    "gz": gz[i]
                })
                
    # Create DataFrame and save
    df = pd.DataFrame(data)
    df.to_csv(out_path, index=False)
    
    print(f"\nSuccessfully generated {len(df)} rows ({len(df) // 100} total windows).")
    print(f"Saved mock dataset to '{out_path}'.")
    print("You can now test the training pipeline by running: python pipeline/train_model.py")

if __name__ == "__main__":
    main()
