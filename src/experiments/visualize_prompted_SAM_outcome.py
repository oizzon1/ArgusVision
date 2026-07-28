"""
visualize_prompted_SAM_outcome.py
---------------------------------
Run SAM with BOX or POINT prompts on a single specified image and produce
the identical 3-panel visualization used in the SAM benchmark experiments
(same colors, same layout as evaluate_sam.py best/worst examples).

Prompts are auto-located from the AerialFuseCV dataset GT labels:
    - box   : axis-aligned enclosing box of each labeled OBB
    - point : centroid of each labeled OBB

Output format (per class found in the image):
    Panel 1 – Original image with prompts
                * box   -> cyan rectangles
                * point -> red stars (yellow edge)
    Panel 2 – Ground Truth Mask (green overlay)
    Panel 3 – Predicted Mask (red overlay)

Each output PNG follows the same filename convention as evaluate_sam.py:
    <img_name>_SAM-ViT-<X>-<BOX|POINT>_<class>_iou_<X.XXX>_dice_<X.XXX>.png

Usage examples:
    python src/experiments/visualize_prompted_SAM_outcome.py --image P0003
    python src/experiments/visualize_prompted_SAM_outcome.py --image P0003 --prompt-type point
    python src/experiments/visualize_prompted_SAM_outcome.py --image P0003 --prompt-type box --model vit_h
    python src/experiments/visualize_prompted_SAM_outcome.py --image P0003 --manual-point

With --manual-point an interactive window opens: left-click to drop one or more
seed points, right-click to undo, Enter/middle-click to finish. Each click is the
SAM point prompt; its class is inferred by sampling the GT semantic-mask color at
the clicked pixel (so IoU/DICE are still computed against that class).
"""

import argparse
import sys
import time
import warnings
from pathlib import Path

# ── project root on sys.path ──────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# Suppress SAM FutureWarning at import time
warnings.filterwarnings("ignore", category=FutureWarning, module="segment_anything.build_sam")

import cv2
import numpy as np

# Re-use the benchmark evaluator (contains all loaders, visualizer, metrics).
# These imports do NOT modify the original modules.
from src.experiments.evaluate_sam import SAMBenchmarkEvaluator
from src.models.sam_segmenter import SAMSegmenter
from src.utils.metrics import calculate_mask_iou, calculate_mask_dice


# ── helpers ───────────────────────────────────────────────────────────────────

def find_image(image_name: str, dataset_root: Path):
    """
    Search for the image file in val/train splits or flat merged structure.
    Returns tuple (image_path, labels_path, mask_path) or raises FileNotFoundError.
    """
    stem = Path(image_name).stem  # strip extension if accidentally passed

    candidates = [
        dataset_root,
        dataset_root / "val",
        dataset_root / "train",
    ]

    for base in candidates:
        img = base / "images" / f"{stem}.png"
        if img.exists():
            lbl = base / "labels" / f"{stem}.txt"
            msk = base / "semantic_masks" / f"{stem}_instance_color_RGB.png"
            return img, lbl, msk

    raise FileNotFoundError(
        f"Image '{stem}.png' not found in dataset '{dataset_root}'.\n"
        "Searched: images/, val/images/, train/images/"
    )


def build_prompts(gt_labels, prompt_type: str):
    """
    Build the SAM prompt list from GT labels in the shape SAMSegmenter expects.
        box   -> list of [x1, y1, x2, y2]
        point -> list of [[x, y]]  (point wrapped in a list)
    """
    if prompt_type == "box":
        return [lbl["box_prompt"] for lbl in gt_labels]
    return [[lbl["point_prompt"]] for lbl in gt_labels]


def collect_clicks(image_rgb):
    """
    Open an interactive window and let the user click seed point(s).
        left-click  -> add a point
        right-click -> undo last point
        Enter / middle-click -> finish
    Returns a list of (x, y) float pixel coordinates.
    """
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 12))
    ax.imshow(image_rgb)
    ax.set_title("Left-click = add point  |  Right-click = undo  |  "
                 "Enter / middle-click = done")
    ax.axis("off")
    print("\n🖱️   Click seed point(s) on the image window. "
          "Press Enter (or middle-click) when finished ...")
    try:
        pts = plt.ginput(n=-1, timeout=0)
    finally:
        plt.close(fig)
    return [(float(x), float(y)) for (x, y) in pts]


def classify_click(x, y, gt_rgb_mask, color_to_class):
    """
    Infer the class of a clicked pixel by sampling the GT semantic-mask color.
    Returns a class_id (0-14) or -1 if background / unknown / out of bounds.
    """
    if gt_rgb_mask is None:
        return -1
    h, w = gt_rgb_mask.shape[:2]
    xi, yi = int(round(x)), int(round(y))
    if not (0 <= xi < w and 0 <= yi < h):
        return -1
    color = tuple(int(c) for c in gt_rgb_mask[yi, xi])
    return color_to_class.get(color, -1)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run SAM with BOX or POINT prompts on a single image and "
                    "save benchmark-style visualizations."
    )
    parser.add_argument(
        "--image", required=True,
        help="Image stem name, e.g. P0003 (extension optional)"
    )
    parser.add_argument(
        "--prompt-type", choices=["box", "point"], default="box",
        help="Prompt type auto-located from the dataset labels (default: box)"
    )
    parser.add_argument(
        "--manual-point", action="store_true",
        help="Open the image in a window and click to seed the point prompt(s). "
             "Forces point mode; class is inferred from the GT mask at each click."
    )
    parser.add_argument(
        "--model", choices=["vit_b", "vit_l", "vit_h"], default="vit_b",
        help="SAM model variant to use (default: vit_b)"
    )
    parser.add_argument(
        "--dataset", default="dataset/AerialFuseCV_Refined/val",
        help="Path to the dataset split containing the image "
             "(default: dataset/AerialFuseCV_Refined/val)"
    )
    parser.add_argument(
        "--checkpoint-dir", default="model_checkpoints/SAM",
        help="Directory containing SAM .pth checkpoints"
    )
    parser.add_argument(
        "--output", default="results/sam_evaluation/single_image",
        help="Output directory for visualization PNGs"
    )
    args = parser.parse_args()

    dataset_root   = ROOT / args.dataset
    checkpoint_dir = ROOT / args.checkpoint_dir
    output_dir     = ROOT / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Locate files ───────────────────────────────────────────────────────
    print(f"\n🔍  Looking for image '{args.image}' in {dataset_root} ...")
    try:
        image_path, label_path, mask_path = find_image(args.image, dataset_root)
    except FileNotFoundError as e:
        print(f"❌  {e}")
        sys.exit(1)

    print(f"   ✅  Image : {image_path}")
    print(f"   ✅  Labels: {label_path}")
    print(f"   ✅  Mask  : {mask_path}")

    # ── 2. Load image ─────────────────────────────────────────────────────────
    image_bgr = cv2.imread(str(image_path))
    if image_bgr is None:
        print(f"❌  Could not read image: {image_path}")
        sys.exit(1)
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    h, w = image_rgb.shape[:2]
    print(f"\n📷  Image size: {w} × {h} px")

    # ── 3. Build evaluator (reuses all loaders / visualizer / metrics) ────────
    evaluator = SAMBenchmarkEvaluator(
        dataset_root=str(dataset_root),
        sam_checkpoint_dir=str(checkpoint_dir)
    )

    gt_rgb_mask = None  # may be loaded early in manual mode for click classification

    # ── 4. Build prompts ──────────────────────────────────────────────────────
    if args.manual_point:
        # Manual seeding is point-based by definition.
        args.prompt_type = "point"

        # GT mask is needed up-front to assign each click to a class by color.
        gt_rgb_mask = evaluator.load_ground_truth_mask(str(mask_path))
        color_to_class = {tuple(v): k for k, v in evaluator.class_color_mapping.items()}

        clicks = collect_clicks(image_rgb)
        if not clicks:
            print("❌  No points clicked — nothing to do.")
            sys.exit(1)

        gt_labels = []
        for (x, y) in clicks:
            class_id = classify_click(x, y, gt_rgb_mask, color_to_class)
            gt_labels.append({
                "class_id": class_id,
                "point_prompt": np.array([x, y], dtype=np.float32),
            })

        print(f"📋  {len(gt_labels)} manual point(s):")
        for k, lbl in enumerate(gt_labels):
            cid = lbl["class_id"]
            cname = (evaluator.class_names[cid]
                     if 0 <= cid < len(evaluator.class_names) else "background/unknown")
            px, py = lbl["point_prompt"]
            print(f"       #{k + 1}: ({px:.0f}, {py:.0f}) -> {cname}")

        prompts = build_prompts(gt_labels, args.prompt_type)
    else:
        # ── Load GT labels → prompts (auto-located from dataset) ──────────────
        gt_labels = evaluator.load_ground_truth_labels(str(label_path), w, h)
        if not gt_labels:
            print(f"❌  No ground-truth labels found in {label_path}")
            sys.exit(1)

        print(f"📋  GT instances: {len(gt_labels)}")
        class_counts = {}
        for lbl in gt_labels:
            cname = evaluator.class_names[lbl["class_id"]]
            class_counts[cname] = class_counts.get(cname, 0) + 1
        for cname, cnt in sorted(class_counts.items()):
            print(f"       {cname}: {cnt}")

        prompts = build_prompts(gt_labels, args.prompt_type)

    # ── 5. Load SAM model ─────────────────────────────────────────────────────
    sam_cfg   = evaluator.sam_configs[args.model]
    ckpt_path = sam_cfg["checkpoint"]
    if not ckpt_path.exists():
        print(f"❌  SAM checkpoint not found: {ckpt_path}")
        sys.exit(1)

    config_name = f"{sam_cfg['name']}-{args.prompt_type.upper()}"
    if args.manual_point:
        config_name += "-MANUAL"
    print(f"\n🤖  Loading {sam_cfg['name']} from {ckpt_path.name} ...")
    sam = SAMSegmenter(sam_type=sam_cfg["type"], checkpoint_path=str(ckpt_path))
    device_label = "CUDA 🚀" if sam.device == "cuda" else "CPU 💻"
    print(f"   Device: {device_label}")

    # ── 6. SAM inference ──────────────────────────────────────────────────────
    print(f"\n⚙️   Running SAM with {args.prompt_type.upper()} prompts "
          f"({len(prompts)} prompts) ...")
    t0 = time.time()
    masks = sam.segment(image_rgb, prompts, prompt_type=args.prompt_type)
    elapsed_ms = (time.time() - t0) * 1000
    print(f"   ✅  Done in {elapsed_ms:.0f} ms  ({len(masks)} masks returned)")

    # ── 7. Load GT RGB mask (already loaded in manual mode) ───────────────────
    if gt_rgb_mask is None:
        gt_rgb_mask = evaluator.load_ground_truth_mask(str(mask_path))
    if gt_rgb_mask is None:
        print(f"⚠️   GT mask file not found: {mask_path}")
        print("    Visualizations will show empty GT panels.")

    # ── 8. Group predicted masks by class (union) and collect prompts ─────────
    class_pred_masks = {}    # class_id → list[np.ndarray]
    class_prompts    = {}    # class_id → list[prompt]  (box=[x1,y1,x2,y2], point=[x,y])

    for i, pred_mask in enumerate(masks):
        if i >= len(gt_labels):
            break

        label    = gt_labels[i]
        class_id = label["class_id"]

        # Ensure 2-D
        if pred_mask is not None and pred_mask.ndim == 3:
            pred_mask = pred_mask[0]

        if pred_mask is None or pred_mask.sum() == 0:
            continue

        if class_id not in class_pred_masks:
            class_pred_masks[class_id] = []
            class_prompts[class_id] = []

        class_pred_masks[class_id].append(pred_mask)
        if args.prompt_type == "box":
            class_prompts[class_id].append(label["box_prompt"])
        else:
            class_prompts[class_id].append(label["point_prompt"])

    # ── 9. Save per-class visualizations ─────────────────────────────────────
    print(f"\n🖼️   Saving visualizations to {output_dir} ...\n")
    saved = 0

    for class_id, pred_masks in class_pred_masks.items():
        class_name = (evaluator.class_names[class_id]
                      if 0 <= class_id < len(evaluator.class_names)
                      else "manual_point")

        # Union of predicted masks
        pred_union = np.zeros((h, w), dtype=bool)
        for pm in pred_masks:
            if pm.shape != pred_union.shape:
                pm = cv2.resize(pm.astype(np.uint8), (w, h),
                                interpolation=cv2.INTER_NEAREST).astype(bool)
            pred_union = np.logical_or(pred_union, pm.astype(bool))

        # GT mask for this class
        if gt_rgb_mask is not None:
            gt_class_mask = evaluator.extract_class_mask(gt_rgb_mask, class_id)
            gt_bool = gt_class_mask.astype(bool) if gt_class_mask is not None \
                else np.zeros((h, w), dtype=bool)
        else:
            gt_bool = np.zeros((h, w), dtype=bool)

        # Metrics
        if gt_bool.sum() > 0:
            iou  = calculate_mask_iou(pred_union, gt_bool)
            dice = calculate_mask_dice(pred_union, gt_bool)
        else:
            iou, dice = 0.0, 0.0

        # Save visualization using the evaluator's method (identical to benchmark)
        evaluator.save_visualization(
            image_rgb   = image_rgb,
            gt_mask     = gt_bool,
            pred_mask   = pred_union,
            class_name  = class_name,
            iou         = iou,
            dice        = dice,
            img_name    = Path(args.image).stem,
            config_name = config_name,
            output_dir  = str(output_dir),
            prompts     = class_prompts[class_id],
            prompt_type = args.prompt_type
        )

        print(f"   [{class_name:>20s}]  IoU: {iou*100:5.1f}%  DICE: {dice*100:5.1f}%  "
              f"({len(pred_masks)} instance{'s' if len(pred_masks) > 1 else ''})")
        saved += 1

    # ── 10. Summary ───────────────────────────────────────────────────────────
    print(f"\n{'─'*55}")
    print(f"✅  {saved} visualization(s) saved to:")
    print(f"   {output_dir}")
    print(f"{'─'*55}\n")


if __name__ == "__main__":
    main()
