import os
import glob
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from features import extract_features_from_df

DATA_DIR = 'data/hw3'
GESTURES = ['UP', 'DOWN', 'LEFT', 'RIGHT']

def load_data():
    X, y = [], []
    for label in GESTURES:
        folder_path = os.path.join(DATA_DIR, label)
        files = glob.glob(os.path.join(folder_path, '*.txt'))
        for file in files:
            df = pd.read_csv(file)
            X.append(extract_features_from_df(df))
            y.append(label)
    return np.array(X), np.array(y)

def main():
    X, y = load_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42, stratify=y)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    svm_model = SVC(kernel='rbf', C=1.0, gamma='scale')
    svm_model.fit(X_train_scaled, y_train)
    
    y_pred = svm_model.predict(X_test_scaled)
    
    print(f"Model Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")
    print(classification_report(y_test, y_pred, zero_division=0))
    print(confusion_matrix(y_test, y_pred))

    os.makedirs('models', exist_ok=True)
    joblib.dump(scaler, 'models/scaler.joblib')
    joblib.dump(svm_model, 'models/classifier.joblib')
    print("Model and scaler saved to 'models/' directory.")

if __name__ == '__main__':
    main()
