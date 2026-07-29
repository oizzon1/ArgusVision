"""
ArgusVision Branding and Logo Display

Model-agnostic pipeline branding that emphasizes the architecture
(Detection → Segmentation → Results) rather than specific model implementations.

Future models can be easily swapped:
- Detectors: YOLO, DETR, Faster R-CNN, etc.
- Segmenters: SAM, FastSAM, MobileSAM, etc.
"""


def display_logo():
    """
    Display ArgusVision satellite-themed logo with model-agnostic pipeline stages.
    
    The logo emphasizes the pipeline architecture rather than specific models,
    making it future-proof as new detectors and segmenters are integrated.
    """
    logo = """
    🛰️  ═══════════════════════════════════════════════ 🛰️
         
                 A R G U S   V I S I O N

      🔍 Detection  →  ✂️  Segmentation  →  🗺️  Results
               Aerial Feature Extraction System
                 By Panagiotis Fragkos
    🛰️  ═══════════════════════════════════════════════ 🛰️
    """
    print(logo)


def display_compact_header():
    """Display compact ArgusVision header for progress updates"""
    return "🛰️ ArgusVision  |  Detection → Segmentation System"


# Emoji reference for documentation
EMOJI_MEANINGS = {
    '🛰️': 'Satellite - Remote sensing, aerial imagery',
    '🔍': 'Detection stage - Any object detector (YOLO, DETR, etc.)',
    '✂️': 'Segmentation stage - Any segmenter (SAM, FastSAM, etc.)',
    '🗺️': 'Results - Geospatial output, segmentation masks',
}


if __name__ == '__main__':
    # Test logo display
    display_logo()
    print("\n" + display_compact_header())
    print("\n📖 Emoji Meanings:")
    for emoji, meaning in EMOJI_MEANINGS.items():
        print(f"   {emoji} - {meaning}")
