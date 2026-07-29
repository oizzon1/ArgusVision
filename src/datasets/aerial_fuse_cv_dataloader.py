import os
import glob
from PIL import Image
import torch
from torch.utils.data import Dataset
import numpy as np

class AerialFuseCVDataset(Dataset):
    """
PyTorch Dataset dataloader for the AerialFuseCV dataset.

    This dataset is designed for multi-task learning, providing:
    1. Image: The input aerial image.
    2. OBB Labels: Oriented bounding box annotations in YOLO format.
    3. Semantic Mask: An RGB color-coded semantic segmentation mask.

    Args:
        root_dir (str): The root directory of the AerialFuseCV dataset.
        split (str): The dataset split to load ('train' or 'val').
        transform (callable, optional): Optional transform to be applied on a sample.
    """
    def __init__(self, root_dir, split='train', transform=None):
        self.root_dir = root_dir
        self.split = split
        self.transform = transform

        self.image_dir = os.path.join(self.root_dir, self.split, 'images')
        self.label_dir = os.path.join(self.root_dir, self.split, 'labels')
        self.mask_dir = os.path.join(self.root_dir, self.split, 'semantic_masks')

        self.image_files = sorted(glob.glob(os.path.join(self.image_dir, '*.png')))
        
        # Verify that all corresponding files exist
        self.verify_files()

    def verify_files(self):
        """
        Verify that for each image, a corresponding label and mask file exists.
        This prevents errors during training if files are missing.
        """
        for img_path in self.image_files:
            base_filename = os.path.splitext(os.path.basename(img_path))[0]
            label_path = os.path.join(self.label_dir, f"{base_filename}.txt")
            mask_path = os.path.join(self.mask_dir, f"{base_filename}.png")
            if not os.path.exists(label_path):
                raise FileNotFoundError(f"Label file not found for image: {img_path}")
            if not os.path.exists(mask_path):
                raise FileNotFoundError(f"Mask file not found for image: {img_path}")

    def load_yolo_obb(self, label_path):
        """
        Load YOLO OBB labels from a text file.
        Each line: class_id x1 y1 x2 y2 x3 y3 x4 y4
        """
        labels = []
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    class_id = int(parts[0])
                    coords = [float(p) for p in parts[1:]]
                    labels.append({'class_id': class_id, 'poly': coords})
        return labels

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        # Load Image
        image_path = self.image_files[idx]
        image = Image.open(image_path).convert('RGB')

        # Load OBB Label
        base_filename = os.path.splitext(os.path.basename(image_path))[0]
        label_path = os.path.join(self.label_dir, f"{base_filename}.txt")
        obb_labels = self.load_yolo_obb(label_path)

        # Load Semantic Mask
        mask_path = os.path.join(self.mask_dir, f"{base_filename}.png")
        semantic_mask = Image.open(mask_path).convert('RGB')

        sample = {
            'image': image,
            'obb_labels': obb_labels,
            'semantic_mask': semantic_mask,
            'filename': os.path.basename(image_path)
        }

        if self.transform:
            sample = self.transform(sample)

        return sample
