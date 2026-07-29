"""Single source of domain truth for ArgusVision.

Every constant here previously existed as multiple hand-maintained copies in the
thesis-era codebase (CLASS_NAMES x3 variants, iSAID color table x4, GSD loading
x4 — see TODO_RESTRUCTURE.md finding F4). Nothing outside this module may
redefine them.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

# DOTA v1.0 class names, in canonical index order (DOTAv1.yaml standard).
# This ordering is shared by DOTA labels, AerialFuseCV, and all model outputs.
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

NUM_DOTA_CLASSES = len(DOTA_CLASS_NAMES)
ALL_DOTA_CLASS_IDS = frozenset(range(NUM_DOTA_CLASSES))

CLASS_ID_TO_NAME: Dict[int, str] = dict(enumerate(DOTA_CLASS_NAMES))
CLASS_NAME_TO_ID: Dict[str, int] = {name: i for i, name in enumerate(DOTA_CLASS_NAMES)}

# iSAID semantic-mask base colors (RGB) -> DOTA class id.
# iSAID encodes instances by perturbing one channel around these base values.
# Two entries were historically wrong in some copies and fixed during the thesis:
# storage-tank (was 0,63,6) and bridge (was 0,127,163) — these are the correct ones.
ISAID_COLOR_TO_CLASS_ID: Dict[Tuple[int, int, int], int] = {
    (0, 127, 255): 0,   # plane
    (0, 0, 63): 1,      # ship
    (0, 63, 63): 2,     # storage-tank
    (0, 63, 0): 3,      # baseball-diamond
    (0, 63, 127): 4,    # tennis-court
    (0, 63, 191): 5,    # basketball-court
    (0, 63, 255): 6,    # ground-track-field
    (0, 100, 155): 7,   # harbor
    (0, 127, 63): 8,    # bridge
    (0, 127, 127): 9,   # large-vehicle
    (0, 0, 127): 10,    # small-vehicle
    (0, 0, 191): 11,    # helicopter
    (0, 191, 127): 12,  # roundabout
    (0, 127, 191): 13,  # soccer-ball-field
    (0, 0, 255): 14,    # swimming-pool
}

CLASS_ID_TO_ISAID_COLOR: Dict[int, Tuple[int, int, int]] = {
    class_id: color for color, class_id in ISAID_COLOR_TO_CLASS_ID.items()
}

# COCO (ground imagery) -> DOTA (aerial) class mapping for zero-shot VBB
# evaluation. Only these four DOTA classes have reasonable COCO counterparts.
COCO_TO_DOTA: Dict[int, int] = {
    2: 10,  # car -> small-vehicle
    4: 0,   # airplane -> plane
    5: 9,   # bus -> large-vehicle
    7: 9,   # truck -> large-vehicle
    8: 1,   # boat -> ship
}

VBB_EVAL_CLASS_IDS = sorted(set(COCO_TO_DOTA.values()))

# Ground-sample-distance per DOTA image (image id -> GSD in m/px), extracted
# from DOTA metadata by dataset/extract_gsd_mapping.py. Path is relative to the
# repo root — the run-from-repo-root convention applies here as everywhere.
# NOTE: legacy code hardcoded dataset/dota_gsd_mapping.json (no DOTA_v1/), a
# location where the file does not exist in the current tree — combined with a
# silent empty-dict fallback, GSD loading was a no-op at all 4 legacy call
# sites. This is the actual location.
DEFAULT_GSD_MAPPING_PATH = Path("dataset/DOTA_v1/dota_gsd_mapping.json")


def load_gsd_mapping(path: Optional[Path] = None) -> Dict[str, float]:
    """Load the DOTA GSD mapping; empty dict if the file is absent."""
    gsd_path = Path(path) if path is not None else DEFAULT_GSD_MAPPING_PATH
    if not gsd_path.exists():
        return {}
    with open(gsd_path) as f:
        return json.load(f)


def identity_class_map(num_classes: int = NUM_DOTA_CLASSES) -> Dict[int, int]:
    """Identity class mapping for datasets already aligned with model indices."""
    return {i: i for i in range(num_classes)}
