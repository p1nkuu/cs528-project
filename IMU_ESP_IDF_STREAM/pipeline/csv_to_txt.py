import os
import argparse
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="Convert combined CSV dataset to individual TXT files.")
    parser.add_argument("--input", type=str, required=True, help="Input CSV file path")
    parser.add_argument("--out_dir", type=str, default="data/converted", help="Output directory base path")
    args = parser.parse_args()

    input_file = args.input
    out_base_dir = args.out_dir

    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return

    print(f"Loading data from {input_file}...")
    df = pd.read_csv(input_file)

    required_cols = ['window_id', 'timestamp_ms', 'label', 'ax', 'ay', 'az', 'gx', 'gy', 'gz']
    for col in required_cols:
        if col not in df.columns:
            print(f"Error: Missing required column '{col}' in the CSV.")
            return

    # Group by label and window_id. Each group is one discrete recording.
    groups = df.groupby(['label', 'window_id'])
    
    print(f"Found {len(groups)} distinct events.")

    for (label, window_id), group in groups:
        # Sort by timestamp just in case
        group = group.sort_values('timestamp_ms')
        
        # Calculate DeltaTime_s
        start_time = group['timestamp_ms'].iloc[0]
        group['DeltaTime_s'] = (group['timestamp_ms'] - start_time) / 1000.0

        # Rename columns to match imu_reader.py output format
        group = group.rename(columns={
            'ax': 'AccelX',
            'ay': 'AccelY',
            'az': 'AccelZ',
            'gx': 'GyroX',
            'gy': 'GyroY',
            'gz': 'GyroZ'
        })
        
        # Add dummy Temp column
        group['Temp'] = 0.00
        
        # Select and order the final columns
        final_cols = ['DeltaTime_s', 'AccelX', 'AccelY', 'AccelZ', 'GyroX', 'GyroY', 'GyroZ', 'Temp']
        out_df = group[final_cols]
        
        # Create sub-directory
        label_str = str(label)
        folder_name = label_str.lower()
        file_prefix = label_str.upper()
        
        target_dir = os.path.join(out_base_dir, folder_name)
        os.makedirs(target_dir, exist_ok=True)
        
        # Find next available filename
        counter = 0
        while True:
            filename = f"{file_prefix}_{counter:02d}.txt"
            output_file = os.path.join(target_dir, filename)
            if not os.path.exists(output_file):
                break
            counter += 1
            
        out_df.to_csv(output_file, index=False, float_format='%.6f')
        print(f"Saved: {output_file} (Window ID: {window_id}, {len(out_df)} samples)")

    print("Done!")

if __name__ == "__main__":
    main()
