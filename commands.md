# Restore ΑΤΗΕΝΑ
ATHENA, read THESIS_NOTES.md and WORK_LOG.md to restore full project context

# Evaluate YOLO Detector
## Vertical Bounding Boxes
python -m src.experiments.evaluate_yolo_vbb
## Oriented Bounding Boxes
python -m src.experiments.evaluate_yolo_obb

# Evaluate SAM Segmenter
## Test mode (10 images)
python src/experiments/evaluate_sam.py --test

## Full evaluation
python src/experiments/evaluate_sam.py