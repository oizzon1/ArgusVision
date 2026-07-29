"""Coherence tests for argusvision.data.constants — the single source of domain truth."""

from argusvision.data import (
    ALL_DOTA_CLASS_IDS,
    CLASS_ID_TO_ISAID_COLOR,
    CLASS_ID_TO_NAME,
    CLASS_NAME_TO_ID,
    COCO_TO_DOTA,
    DOTA_CLASS_NAMES,
    ISAID_COLOR_TO_CLASS_ID,
    NUM_DOTA_CLASSES,
    VBB_EVAL_CLASS_IDS,
    identity_class_map,
    load_gsd_mapping,
)


def test_class_names_canonical_order():
    assert NUM_DOTA_CLASSES == 15
    assert DOTA_CLASS_NAMES[0] == "plane"
    assert DOTA_CLASS_NAMES[10] == "small-vehicle"
    assert DOTA_CLASS_NAMES[14] == "swimming-pool"
    assert len(set(DOTA_CLASS_NAMES)) == NUM_DOTA_CLASSES


def test_name_id_mappings_are_inverses():
    assert all(CLASS_NAME_TO_ID[CLASS_ID_TO_NAME[i]] == i for i in range(NUM_DOTA_CLASSES))
    assert ALL_DOTA_CLASS_IDS == frozenset(range(NUM_DOTA_CLASSES))


def test_isaid_color_table_bijective_and_complete():
    assert len(ISAID_COLOR_TO_CLASS_ID) == NUM_DOTA_CLASSES
    assert set(ISAID_COLOR_TO_CLASS_ID.values()) == set(range(NUM_DOTA_CLASSES))
    assert all(
        ISAID_COLOR_TO_CLASS_ID[CLASS_ID_TO_ISAID_COLOR[i]] == i
        for i in range(NUM_DOTA_CLASSES)
    )
    # The two historically miscopied values, pinned to their corrected colors.
    assert CLASS_ID_TO_ISAID_COLOR[CLASS_NAME_TO_ID["storage-tank"]] == (0, 63, 63)
    assert CLASS_ID_TO_ISAID_COLOR[CLASS_NAME_TO_ID["bridge"]] == (0, 127, 63)


def test_coco_mapping_targets_exist():
    assert set(COCO_TO_DOTA.values()) <= ALL_DOTA_CLASS_IDS
    assert VBB_EVAL_CLASS_IDS == sorted(set(COCO_TO_DOTA.values()))


def test_identity_class_map():
    m = identity_class_map()
    assert len(m) == NUM_DOTA_CLASSES and m[7] == 7


def test_gsd_mapping_loads_from_repo_root():
    gsd = load_gsd_mapping()
    assert isinstance(gsd, dict) and len(gsd) > 0, (
        "expected dataset/dota_gsd_mapping.json when run from repo root"
    )
    assert all(isinstance(v, float) for v in gsd.values())


def test_gsd_mapping_missing_path_returns_empty():
    assert load_gsd_mapping("does/not/exist.json") == {}
