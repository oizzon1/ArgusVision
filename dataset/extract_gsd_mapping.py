"""
Extract GSD (Ground Sample Distance) from original DOTA labels and create mapping.

This script parses all original DOTA label files (train, val, test) and extracts
the GSD metadata from line 2 of each file, creating a JSON mapping file.

Output: dataset/dota_gsd_mapping.json
Format: {"P0000": 0.146343590398, "P0001": 0.182451...}
"""

import json
from pathlib import Path
from tqdm import tqdm

def extract_gsd_mapping():
    """Extract GSD from all original DOTA labels and save mapping."""
    
    gsd_mapping = {}
    base_path = Path("dataset/DOTA_v1")
    
    # Process train, val, and test splits
    for split in ["train", "val", "test"]:
        labels_dir = base_path / split / "labels"
        
        if not labels_dir.exists():
            print(f"WARNING: {split} labels not found: {labels_dir}")
            continue
        
        label_files = list(labels_dir.glob("*.txt"))
        print(f"\nProcessing {split} split: {len(label_files)} files")
        
        for label_file in tqdm(label_files, desc=f"Extracting GSD from {split}"):
            try:
                with open(label_file, 'r') as f:
                    lines = f.readlines()
                    
                    # Line 2 contains: gsd:0.146343590398
                    if len(lines) >= 2:
                        gsd_line = lines[1].strip()
                        if gsd_line.startswith("gsd:"):
                            gsd_value = float(gsd_line.split(':')[1])
                            image_id = label_file.stem  # e.g., "P0000"
                            gsd_mapping[image_id] = gsd_value
            except Exception as e:
                print(f"ERROR: Error processing {label_file.name}: {e}")
    
    # Save mapping
    output_file = Path("dataset/dota_gsd_mapping.json")
    with open(output_file, 'w') as f:
        json.dump(gsd_mapping, f, indent=2)
    
    print(f"\nGSD mapping saved: {output_file}")
    print(f"Total images: {len(gsd_mapping)}")
    
    # Statistics
    gsd_values = list(gsd_mapping.values())
    print(f"\nGSD Statistics:")
    print(f"   Min: {min(gsd_values):.4f}m")
    print(f"   Max: {max(gsd_values):.4f}m")
    print(f"   Mean: {sum(gsd_values)/len(gsd_values):.4f}m")
    
    return gsd_mapping

if __name__ == "__main__":
    print("="*80)
    print("DOTA GSD EXTRACTION".center(80))
    print("="*80)
    
    gsd_mapping = extract_gsd_mapping()
    
    print("\n" + "="*80)
    print("GSD extraction complete!".center(80))
    print("="*80)
