import pandas as pd
import os
import glob
from tqdm import tqdm

def merge_csvs():
    input_pattern = "data/species_raw/*.csv"
    output_file = "data/perenual_data.csv"
    
    files = glob.glob(input_pattern)
    if not files:
        print("No files found in data/species_raw/")
        return

    print(f"Found {len(files)} files. Merging...")
    
    print(f"Found {len(files)} files. Merging...")

    # Step 1: Discover all columns (Union of schemas)
    print("Scanning schemas...")
    all_columns = set()
    for f in tqdm(files, desc="Scanning Headers"):
        try:
            # Read only header
            cols = pd.read_csv(f, nrows=0).columns.tolist()
            all_columns.update(cols)
        except pd.errors.EmptyDataError:
            continue
    
    final_columns = sorted(list(all_columns)) # Sort for consistency
    print(f"Total unique columns found: {len(final_columns)}")

    # Step 2: Iterative Append with open file handle
    print("Merging data...")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f_out:
        # Write header first
        pd.DataFrame(columns=final_columns).to_csv(f_out, index=False)
        
        for f in tqdm(files, desc="Writing Data"):
            try:
                df = pd.read_csv(f)
                # Align columns to the master schema (add missing as NaN)
                df = df.reindex(columns=final_columns)
                # Append to the open file handle
                df.to_csv(f_out, header=False, index=False)
            except pd.errors.EmptyDataError:
                continue

    print(f"Done! Merged data saved to {output_file}")

if __name__ == "__main__":
    merge_csvs()
