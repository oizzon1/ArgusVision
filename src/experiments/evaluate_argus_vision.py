import torch
from torch.utils.data import DataLoader
from src.datasets.aerial_fuse_cv_dataloader import AerialFuseCVDataset
from src.argus_vision.argus_vision_core import ArgusVision
from src.models.yolo_detector import YOLODetector # Assuming this exists
from src.models.sam_segmenter import SAMSegmenter # Assuming this exists
from src.utils.metrics import calculate_mask_iou, calculate_mask_dice # Assuming these will be implemented

class ArgusVisionEvaluator:
    """
    Evaluates the ArgusVision pipeline on a given dataset split.
    """
    def __init__(self, dataset_root, split='val', batch_size=16, num_workers=0):
        self.dataset_root = dataset_root
        self.split = split
        self.batch_size = batch_size
        self.num_workers = num_workers

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Initialize models (placeholders for now)
        # In a real scenario, these would be loaded from checkpoints
        self.yolo_model = YOLODetector(model_path="path/to/yolo_model.pt", device=self.device)
        self.sam_model = SAMSegmenter(model_path="path/to/sam_model.pt", device=self.device)
        
        self.argus_vision_pipeline = ArgusVision(self.yolo_model, self.sam_model)

        self.dataset = AerialFuseCVDataset(root_dir=self.dataset_root, split=self.split)
        self.dataloader = DataLoader(
            self.dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            collate_fn=self.collate_fn # Custom collate_fn for handling variable-length labels
        )

    def collate_fn(self, batch):
        """
        Custom collate function to handle variable number of OBB labels per image.
        """
        images = [item['image'] for item in batch]
        obb_labels = [item['obb_labels'] for item in batch]
        semantic_masks = [item['semantic_mask'] for item in batch]
        filenames = [item['filename'] for item in batch]
        
        # Convert PIL Images to tensors if a transform is not already doing it
        # For now, we'll keep them as PIL images until transforms are defined
        
        return {
            'images': images,
            'obb_labels': obb_labels,
            'semantic_masks': semantic_masks,
            'filenames': filenames
        }

    def evaluate(self):
        """
        Runs the evaluation pipeline and computes metrics.
        """
        self.yolo_model.eval()
        self.sam_model.eval()

        all_mask_ious = []
        all_mask_dices = []

        with torch.no_grad():
            for i, batch in enumerate(self.dataloader):
                images = batch['images']
                gt_obb_labels = batch['obb_labels']
                gt_semantic_masks = batch['semantic_masks']
                filenames = batch['filenames']

                for j, image_pil in enumerate(images):
                    # Run ArgusVision pipeline for each image
                    pipeline_results = self.argus_vision_pipeline.run_pipeline(image_pil)
                    
                    predicted_masks = pipeline_results['segmentation_masks']
                    # Assuming gt_semantic_masks[j] is a PIL Image and predicted_masks is a list of numpy bool arrays
                    
                    # For simplicity, let's assume we have one ground truth mask per image
                    # and we want to compare it against the first predicted mask if multiple exist
                    if predicted_masks and gt_semantic_masks[j]:
                        # Convert PIL Image to numpy array for metric calculation
                        gt_mask_np = np.array(gt_semantic_masks[j].convert('L')) > 0 # Convert to binary
                        
                        # Assuming predicted_masks contains a single mask or we take the first one
                        pred_mask_np = predicted_masks[0] # This needs to be a binary numpy array
                        
                        iou = calculate_mask_iou(pred_mask_np, gt_mask_np)
                        dice = calculate_mask_dice(pred_mask_np, gt_mask_np)
                        
                        all_mask_ious.append(iou)
                        all_mask_dices.append(dice)
                        
                        print(f"Processed {filenames[j]}: IoU={iou:.4f}, DICE={dice:.4f}")
                    else:
                        print(f"Processed {filenames[j]}: No predicted masks or ground truth mask found.")

        mean_iou = np.mean(all_mask_ious) if all_mask_ious else 0
        mean_dice = np.mean(all_mask_dices) if all_mask_dices else 0

        print(f"\n--- Evaluation Summary ({self.split.capitalize()} Split) ---")
        print(f"Mean Mask IoU: {mean_iou:.4f}")
        print(f"Mean Mask DICE: {mean_dice:.4f}")
        
        return {"mean_iou": mean_iou, "mean_dice": mean_dice}

if __name__ == "__main__":
    # Example usage
    # Ensure you have a dummy AerialFuseCV dataset structure for this to run
    # e.g., dataset/AerialFuseCV/val/images/, dataset/AerialFuseCV/val/labels/, dataset/AerialFuseCV/val/semantic_masks/
    
    # For testing, you might need to create dummy files or point to a small subset
    # For instance, create a dummy image and corresponding empty label/mask files
    
    # root_dir = 'dataset/AerialFuseCV' # Adjust this path as needed
    # evaluator = ArgusVisionEvaluator(root_dir=root_dir, split='val', batch_size=1)
    # results = evaluator.evaluate()
    # print(results)
    print("ArgusVision Evaluator script created. Please uncomment and configure for testing.")
