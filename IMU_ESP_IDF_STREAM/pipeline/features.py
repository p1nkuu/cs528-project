import numpy as np

def get_active_window(data_array, window_size=100):
    if len(data_array) <= window_size:
        return data_array
        
    max_energy = -1
    best_start = 0
    
    for i in range(len(data_array) - window_size + 1):
        window = data_array[i:i+window_size]
        energy = np.sum(np.var(window, axis=0))
        if energy > max_energy:
            max_energy = energy
            best_start = i
            
    return data_array[best_start:best_start+window_size]

def extract_features_from_df(df):
    features = []
    cols = ['AccelX', 'AccelY', 'AccelZ', 'GyroX', 'GyroY', 'GyroZ']
    
    data_array = df[cols].values
    active_data = get_active_window(data_array)
    
    for col_idx in range(6):
        data = active_data[:, col_idx]
        data_centered = data - np.mean(data)
        features.extend([
            np.mean(data),
            np.std(data),
            np.max(data_centered),
            np.min(data_centered),
            np.median(data_centered),
            np.sqrt(np.mean(data_centered**2))
        ])
        
    axes_means = np.mean(active_data, axis=0)
    features.append(np.argmax(axes_means))
    features.append(np.argmin(axes_means))
    
    return features

def extract_features_from_array(data_array):
    features = []
    active_data = get_active_window(data_array)
    
    for col_idx in range(6):
        data = active_data[:, col_idx]
        data_centered = data - np.mean(data)
        features.extend([
            np.mean(data),
            np.std(data),
            np.max(data_centered),
            np.min(data_centered),
            np.median(data_centered),
            np.sqrt(np.mean(data_centered**2))
        ])
        
    axes_means = np.mean(active_data, axis=0)
    features.append(np.argmax(axes_means))
    features.append(np.argmin(axes_means))
    
    return features
