import os
import argparse
import shutil
import glob

def merge_folders(sources, out_dir):
    """
    Merges multiple source folders containing label sub-directories (like 'down', 'up')
    into a single output directory. Files are renamed sequentially to avoid collisions.
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # Find all unique label sub-directories across all sources
    all_labels = set()
    for source in sources:
        if os.path.exists(source) and os.path.isdir(source):
            for label in os.listdir(source):
                label_path = os.path.join(source, label)
                if os.path.isdir(label_path):
                    all_labels.add(label)

    # For each label, rename and copy files to the output directory
    for label in all_labels:
        out_label_dir = os.path.join(out_dir, label)
        if not os.path.exists(out_label_dir):
            os.makedirs(out_label_dir)

        # To allow multiple runs without colliding, we find the highest existing index in out_label_dir
        existing_files = glob.glob(os.path.join(out_label_dir, f"{label.upper()}_*.txt"))
        file_counter = 0
        if existing_files:
            indices = []
            for f in existing_files:
                basename = os.path.basename(f)
                num_str = basename.replace(label.upper() + "_", "").replace(".txt", "")
                if num_str.isdigit():
                    indices.append(int(num_str))
            if indices:
                file_counter = max(indices) + 1

        label_prefix = label.upper()

        for source in sources:
            source_label_dir = os.path.join(source, label)
            if os.path.exists(source_label_dir) and os.path.isdir(source_label_dir):
                # Process all txt files in this source's label directory
                txt_files = sorted(glob.glob(os.path.join(source_label_dir, "*.txt")))
                for txt_file in txt_files:
                    new_filename = f"{label_prefix}_{file_counter:02d}.txt"
                    new_filepath = os.path.join(out_label_dir, new_filename)
                    
                    # Copy over to new location
                    shutil.copy2(txt_file, new_filepath)
                    file_counter += 1

        print(f"Merged files for label '{label}' into {out_label_dir}. Next available index is {file_counter}")

def main():
    parser = argparse.ArgumentParser(description="Merge multiple label folders into one sequentially.")
    parser.add_argument("--sources", nargs="+", required=True, help="List of source directory paths to merge.")
    parser.add_argument("--out", required=True, help="Destination directory path.")
    args = parser.parse_args()

    merge_folders(args.sources, args.out)
    print(f"Successfully merged all folders into {args.out}")

if __name__ == "__main__":
    main()
