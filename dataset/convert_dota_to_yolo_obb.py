"""
Convert DOTA v1 original format to YOLO OBB (Oriented Bounding Box) format.
Preserves rotation by keeping all 8 coordinates (4 corners).
"""
from pathlib import Path
from PIL import Image
from collections import Counter
import shutil

# Class name to ID mapping (DOTAv1.yaml)
CLASS_NAME_TO_ID = {
    'plane': 0,
    'ship': 1,
    'storage-tank': 2,
    'baseball-diamond': 3,
    'tennis-court': 4,
    'basketball-court': 5,
    'ground-track-field': 6,
    'harbor': 7,
    'bridge': 8,
    'large-vehicle': 9,
    'small-vehicle': 10,
    'helicopter': 11,
    'roundabout': 12,
    'soccer-ball-field': 13,
    'swimming-pool': 14
}

def get_image_dimensions(image_path):
    """Get image width and height."""
    with Image.open(image_path) as img:
        return img.size  # (width, height)

def convert_label_file(original_label_path, output_label_path, image_path):
    """Convert a single label file from DOTA to YOLO OBB format."""
    # Get image dimensions for normalization
    img_w, img_h = get_image_dimensions(image_path)
    
    # Read original label
    with open(original_label_path, 'r') as f:
        lines = f.readlines()
    
    # Skip header lines and parse annotations
    output_lines = []
    instances_by_class = Counter()
    
    for line in lines:
        # Skip header lines
        if line.startswith('imagesource') or line.startswith('gsd'):
            continue
        
        parts = line.strip().split()
        if len(parts) < 10:
            continue
        
        try:
            # Parse coordinates and class
            x1, y1, x2, y2, x3, y3, x4, y4 = map(float, parts[:8])
            class_name = parts[8]
            # difficulty = int(parts[9])  # We discard this for now
            
            # Convert class name to ID
            if class_name not in CLASS_NAME_TO_ID:
                print(f"Warning: Unknown class '{class_name}' in {original_label_path}")
                continue
            
            class_id = CLASS_NAME_TO_ID[class_name]
            instances_by_class[class_id] += 1
            
            # Normalize coordinates
            x1_norm = x1 / img_w
            y1_norm = y1 / img_h
            x2_norm = x2 / img_w
            y2_norm = y2 / img_h
            x3_norm = x3 / img_w
            y3_norm = y3 / img_h
            x4_norm = x4 / img_w
            y4_norm = y4 / img_h
            
            # Format: class_id x1 y1 x2 y2 x3 y3 x4 y4 (all normalized)
            output_line = f"{class_id} {x1_norm:.6f} {y1_norm:.6f} {x2_norm:.6f} {y2_norm:.6f} {x3_norm:.6f} {y3_norm:.6f} {x4_norm:.6f} {y4_norm:.6f}\n"
            output_lines.append(output_line)
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing line in {original_label_path}: {line.strip()}")
            continue
    
    # Write converted label
    output_label_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_label_path, 'w') as f:
        f.writelines(output_lines)
    
    return instances_by_class

def create_image_symlinks(source_dir, target_dir):
    """Create symlinks to original images (avoids duplication)."""
    target_dir.mkdir(parents=True, exist_ok=True)
    
    for img_file in source_dir.glob('*.png'):
        target_path = target_dir / img_file.name
        if not target_path.exists():
            # On Windows, create a copy instead of symlink if symlink fails
            try:
                target_path.symlink_to(img_file.resolve())
            except OSError:
                shutil.copy2(img_file, target_path)

def convert_dataset():
    """Convert entire DOTA v1 dataset to YOLO OBB format."""
    source_root = Path("dataset/DOTA_v1")
    target_root = Path("dataset/DOTA_v1_YOLO_oriented_bboxes_dataset")
    
    print("=" * 80)
    print("DOTA v1 to YOLO OBB Conversion")
    print("=" * 80)
    print(f"Source: {source_root}")
    print(f"Target: {target_root}")
    print()
    
    total_instances = Counter()
    total_files = 0
    
    # Process train and val splits
    for split in ['train', 'val']:
        print(f"\nProcessing {split} split...")
        
        source_labels_dir = source_root / split / 'labels'
        source_images_dir = source_root / split / 'images'
        target_labels_dir = target_root / 'labels' / split
        target_images_dir = target_root / 'images' / split
        
        if not source_labels_dir.exists():
            print(f"  Warning: {source_labels_dir} not found, skipping...")
            continue
        
        # Create image symlinks
        print(f"  Creating image links...")
        create_image_symlinks(source_images_dir, target_images_dir)
        
        # Convert labels
        label_files = list(source_labels_dir.glob('*.txt'))
        print(f"  Converting {len(label_files)} label files...")
        
        for i, label_file in enumerate(label_files):
            # Find corresponding image
            image_file = source_images_dir / f"{label_file.stem}.png"
            
            if not image_file.exists():
                print(f"  Warning: Image not found for {label_file.name}")
                continue
            
            # Convert label
            output_label = target_labels_dir / label_file.name
            instances = convert_label_file(label_file, output_label, image_file)
            total_instances.update(instances)
            total_files += 1
            
            # Progress indicator
            if (i + 1) % 100 == 0:
                print(f"    Processed {i + 1}/{len(label_files)} files...")
        
        print(f"  Completed {split}: {len(label_files)} files")
    
    # Print statistics
    print("\n" + "=" * 80)
    print("Conversion Complete!")
    print("=" * 80)
    print(f"Total files converted: {total_files}")
    print(f"Total instances: {sum(total_instances.values())}")
    print("\nInstances per class:")
    
    # Sort by class ID
    for class_id in sorted(total_instances.keys()):
        class_name = [name for name, cid in CLASS_NAME_TO_ID.items() if cid == class_id][0]
        count = total_instances[class_id]
        print(f"  {class_id:2d} ({class_name:20s}): {count:6,d}")
    
    print("\nOutput directories:")
    print(f"  Labels: {target_root / 'labels'}")
    print(f"  Images: {target_root / 'images'}")
    print("=" * 80)

if __name__ == "__main__":
    convert_dataset()
