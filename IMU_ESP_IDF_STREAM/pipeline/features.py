import numpy as np

import config


def get_active_window(data_array, window_size=None):
    """Return the most energetic sub-window for motion-focused features."""
    if window_size is None:
        window_size = config.SAMPLES_PER_WINDOW

    if len(data_array) <= window_size:
        return data_array

    max_energy = -1.0
    best_start = 0

    for i in range(len(data_array) - window_size + 1):
        window = data_array[i : i + window_size]
        energy = np.sum(np.var(window, axis=0))
        if energy > max_energy:
            max_energy = energy
            best_start = i

    return data_array[best_start : best_start + window_size]


def extract_features_from_array(data_array, window_size=None):
    """Extracts statistical features from a (N, 6) window."""
    active_data = get_active_window(data_array, window_size=window_size)
    features = []

    for col_idx in range(6):
        data = active_data[:, col_idx]
        data_centered = data - np.mean(data)
        features.extend(
            [
                float(np.mean(data)),
                float(np.std(data)),
                float(np.max(data_centered)),
                float(np.min(data_centered)),
                float(np.median(data_centered)),
                float(np.sqrt(np.mean(data_centered ** 2))),
            ]
        )

    axes_means = np.mean(active_data, axis=0)
    features.append(float(np.argmax(axes_means)))
    features.append(float(np.argmin(axes_means)))

    return features
