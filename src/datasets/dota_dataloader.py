DOTA_CLASS_NAMES = [
    "plane",
    "ship",
    "storage-tank",
    "baseball-diamond",
    "tennis-court",
    "basketball-court",
    "ground-track-field",
    "harbor",
    "bridge",
    "large-vehicle",
    "small-vehicle",
    "helicopter",
    "roundabout",
    "soccer-ball-field",
    "swimming-pool",
]

NUM_DOTA = len(DOTA_CLASS_NAMES)

# COCO (ground) -> DOTA (aerial) mapping for VBB evaluation.
# Only four DOTA classes have reasonable COCO counterparts.
COCO_TO_DOTA = {
    2: 10,  # car -> small-vehicle
    4: 0,   # airplane -> plane
    5: 9,   # bus -> large-vehicle
    7: 9,   # truck -> large-vehicle
    8: 1,   # boat -> ship
}

VBB_EVAL_CLASS_IDS = sorted(set(COCO_TO_DOTA.values()))
ALL_DOTA_CLASS_IDS = set(range(NUM_DOTA))


def identity_class_map(num_classes: int) -> dict:
    """Return identity class mapping for datasets already aligned with model indices."""
    return {i: i for i in range(num_classes)}
