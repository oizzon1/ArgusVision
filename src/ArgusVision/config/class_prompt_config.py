-"""
Class-specific prompt configuration for ArgusVision pipeline.

This configuration determines which prompt type (box or point) to use for each class
during SAM segmentation. Different object geometries benefit from different prompt types:

- Box prompts: Better for rectangles, large objects, complex shapes
- Point prompts: Better for circular objects where box includes excessive background
  Example: Roundabout with box → includes surrounding roads
           Roundabout with point → only central island

Usage:
    from src.ArgusVision.config.class_prompt_config import CLASS_PROMPT_CONFIG
    prompt_type = CLASS_PROMPT_CONFIG[class_id]  # Returns 'box' or 'point'
"""

# DOTA v1 Class Names (for reference)
CLASS_NAMES = {
    0: 'plane',
    1: 'ship',
    2: 'storage-tank',      # Excluded in AerialFuseCV_Refined (0% match)
    3: 'baseball-diamond',
    4: 'tennis-court',
    5: 'basketball-court',
    6: 'ground-track-field',
    7: 'harbor',
    8: 'bridge',            # Excluded in AerialFuseCV_Refined (0% match)
    9: 'large-vehicle',
    10: 'small-vehicle',
    11: 'helicopter',
    12: 'roundabout',
    13: 'soccer-ball-field',
    14: 'swimming-pool',
}

# Class Prompt Configuration
# EXPERIMENT: Testing point prompts for small/challenging objects
# Original baseline was 'box' for all classes
CLASS_PROMPT_CONFIG = {
    0: 'point',    # plane - EXPERIMENT: test point for small objects
    1: 'box',      # ship - variable shapes → box
    2: 'box',      # storage-tank - excluded but kept for completeness
    3: 'box',      # baseball-diamond - structured diamond shape → box
    4: 'box',      # tennis-court - rectangular → box
    5: 'box',      # basketball-court - rectangular → box
    6: 'box',      # ground-track-field - oval/rectangular → box
    7: 'box',      # harbor - complex infrastructure → box
    8: 'box',      # bridge - excluded but kept for completeness
    9: 'box',      # large-vehicle - standard vehicle shape → box
    10: 'point',   # small-vehicle - EXPERIMENT: test point for small objects
    11: 'point',   # helicopter - EXPERIMENT: test point for small objects
    12: 'point',   # roundabout - EXPERIMENT: test point for circular shape
    13: 'box',     # soccer-ball-field - rectangular → box
    14: 'box',     # swimming-pool - often circular/irregular → box
}

# Future optimization candidates based on SAM Phase 2 results:
# - roundabout (12): Try 'point' to avoid surrounding roads
# - swimming-pool (14): Try 'point' for irregular/circular pools
# - harbor (7): Complex geometry, may benefit from point prompts

# Helper function to get prompt type with fallback
def get_prompt_type(class_id, default='box'):
    """
    Get the configured prompt type for a given class ID.
    
    Args:
        class_id (int): DOTA v1 class ID (0-14)
        default (str): Default prompt type if class_id not found
        
    Returns:
        str: 'box' or 'point'
    """
    return CLASS_PROMPT_CONFIG.get(class_id, default)


# Validation: Ensure all class IDs have valid prompt types
for class_id, prompt_type in CLASS_PROMPT_CONFIG.items():
    assert prompt_type in ['box', 'point'], f"Invalid prompt type '{prompt_type}' for class {class_id}"
