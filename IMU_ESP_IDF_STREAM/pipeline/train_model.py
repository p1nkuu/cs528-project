import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.utils.class_weight import compute_class_weight
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Dropout, Flatten, Dense, Input
from tensorflow.keras.utils import to_categorical
import joblib

import config

# Config
CSV_FILE = config.CSV_FILE
MODEL_NAME = config.MODEL_NAME
SCALER_NAME = config.SCALER_NAME
SAMPLES_PER_WINDOW = config.SAMPLES_PER_WINDOW
FEATURES = config.FEATURES
NUM_FEATURES = len(FEATURES)
EXPECTED_CLASSES = config.EXPECTED_CLASSES

def load_and_preprocess_data(csv_path):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Data file '{csv_path}' not found. Please collect data first.")
        
    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # We group the data by 'window_id'
    grouped = df.groupby('window_id')
    
    X = []
    y = []
    
    for window_id, group in grouped:
        # Only keep complete windows of exactly 100 samples
        if len(group) == SAMPLES_PER_WINDOW:
            X.append(group[FEATURES].values)
            y.append(group['label'].iloc[0]) # All rows in a window have the same label
            
    X = np.array(X)
    y = np.array(y)
    
    print(f"Total valid samples (windows): {X.shape[0]}")
    
    if X.shape[0] == 0:
        raise ValueError("No valid 100-step windows found in dataset.")

    # Flatten X to 2D to apply StandardScaler then reshape back to 3D
    num_samples = X.shape[0]
    X_flat = X.reshape(-1, NUM_FEATURES)
    scaler = StandardScaler()
    X_scaled_flat = scaler.fit_transform(X_flat)
    X = X_scaled_flat.reshape(num_samples, SAMPLES_PER_WINDOW, NUM_FEATURES)

    # Encode string labels ('Left', 'Idle', etc.) to integers (0, 1, 2...)
    encoder = LabelEncoder()
    # Force the encoder to recognize all expected classes, then fit on actual
    encoder.fit(EXPECTED_CLASSES)
    y_encoded = encoder.transform(y)
    
    # One-hot encode the target
    y_categorical = to_categorical(y_encoded, num_classes=len(EXPECTED_CLASSES))
    
    return X, y_categorical, encoder.classes_, scaler

def build_model(input_shape, num_classes):
    model = Sequential([
        Input(shape=input_shape),
        Conv1D(filters=32, kernel_size=3, activation='relu', padding='same'),
        Conv1D(filters=64, kernel_size=3, activation='relu', padding='same'),
        MaxPooling1D(pool_size=2),
        Dropout(0.5),
        Flatten(),
        Dense(128, activation='relu'),
        Dropout(0.5),
        Dense(num_classes, activation='softmax')
    ])
    
    model.compile(optimizer='adam', 
                  loss='categorical_crossentropy', 
                  metrics=['accuracy'])
    return model

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, CSV_FILE)
    
    # 1. Load and process
    try:
        X, y, classes, scaler = load_and_preprocess_data(csv_path)
    except Exception as e:
        print(f"Error during data loading: {e}")
        return

    print(f"Classes found: {classes}")
    print(f"Input shape: {X.shape}") # Should be (N, 100, 6)
    
    # Save the scaler for inference
    out_scaler_path = os.path.join(script_dir, SCALER_NAME)
    joblib.dump(scaler, out_scaler_path)
    print(f"Saved standardization scaler to '{out_scaler_path}'")
    
    # 2. Split train/test (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"Training data size: {X_train.shape[0]} windows")
    print(f"Test data size: {X_test.shape[0]} windows")
    
    # 3. Build & train model
    model = build_model(input_shape=(SAMPLES_PER_WINDOW, NUM_FEATURES), num_classes=len(EXPECTED_CLASSES))
    model.summary()
    
    print("\n--- Starting Training ---")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=30,
        batch_size=16
    )
    
    # 4. Evaluate and save
    loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
    print(f"\nTest Accuracy: {accuracy * 100:.2f}%")
    
    out_model_path = os.path.join(script_dir, MODEL_NAME)
    model.save(out_model_path)
    print(f"Model saved successfully to '{out_model_path}'")

if __name__ == "__main__":
    main()
