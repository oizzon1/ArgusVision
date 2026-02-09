"""
Reformed visualization module for ArgusVision diagnostic evaluation.
Features tight 2x2 grid layout with centered title and color-coded detections.
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont


class DiagnosticVisualizerV2:
    """
    Reformed diagnostic visualization with improved layout.
    
    Layout:
    - Top-left: OBB Detections (color-coded)
    - Top-right: VBB Segmentation Prompts (color-coded)
    - Bottom-left: Ground Truth Masks (green)
    - Bottom-right: Segmented Masks (red)
    """
    
    # Color scheme for detection outcomes
    COLORS = {
        'TP': (0, 255, 0),      # Green
        'FP': (255, 0, 0),       # Red (BGR: Blue component first)
        'FN': (0, 255, 255),     # Yellow (BGR)
        'GT': (0, 255, 0),       # Green for GT masks
        'SEG': (0, 0, 255),      # Red for segmentation masks (BGR)
    }
    
    def __init__(self, panel_size: int = 1024, spacing: int = 10):
        """
        Initialize visualizer.
        
        Args:
            panel_size: Size of each panel (square)
            spacing: Pixels between panels
        """
        self.panel_size = panel_size
        self.spacing = spacing

    def _get_tnr_font(self, size: int, bold: bool = False):
        """Load Times New Roman font with safe fallback."""
        candidates = [
            "C:/Windows/Fonts/timesbd.ttf" if bold else "C:/Windows/Fonts/times.ttf",
            "C:/Windows/Fonts/times.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _draw_centered_tnr_text(
        self,
        image: np.ndarray,
        text: str,
        y: int,
        font_size: int,
        bold: bool = False,
        color: Tuple[int, int, int] = (0, 0, 0),
    ) -> np.ndarray:
        """Draw centered Times New Roman text on an RGB image."""
        pil_img = Image.fromarray(image)
        draw = ImageDraw.Draw(pil_img)
        font = self._get_tnr_font(font_size, bold=bold)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        x = max(0, (image.shape[1] - text_w) // 2)
        draw.text((x, y), text, fill=color, font=font)
        return np.array(pil_img)

    def _draw_detection_legend(self, image: np.ndarray, y: int) -> np.ndarray:
        """Draw colored-dot detection legend centered on one row."""
        pil_img = Image.fromarray(image)
        draw = ImageDraw.Draw(pil_img)

        title = "Detection Bboxes Legend:"
        font = self._get_tnr_font(24, bold=True)
        title_bbox = draw.textbbox((0, 0), title, font=font)
        title_w = title_bbox[2] - title_bbox[0]

        # Dot colors are defined in BGR then converted to RGB for PIL draw.
        entries = [
            ("TP", (0, 255, 0)),   # green
            ("FP", (0, 0, 255)),   # red
            ("FN", (255, 0, 0)),   # blue
        ]
        dot_d = 14
        gap_title_to_entries = 24
        gap_between_entries = 20

        entry_widths = []
        for label, _ in entries:
            label_bbox = draw.textbbox((0, 0), label, font=font)
            label_w = label_bbox[2] - label_bbox[0]
            entry_widths.append(dot_d + 8 + label_w)

        total_w = title_w + gap_title_to_entries + sum(entry_widths) + gap_between_entries * (len(entries) - 1)
        x = max(0, (image.shape[1] - total_w) // 2)

        draw.text((x, y), title, fill=(0, 0, 0), font=font)
        x += title_w + gap_title_to_entries

        for i, (label, bgr) in enumerate(entries):
            rgb = (bgr[2], bgr[1], bgr[0])
            draw.ellipse((x, y + 8, x + dot_d, y + 8 + dot_d), fill=rgb)
            x += dot_d + 8
            draw.text((x, y), label, fill=(0, 0, 0), font=font)
            label_bbox = draw.textbbox((0, 0), label, font=font)
            label_w = label_bbox[2] - label_bbox[0]
            x += label_w
            if i < len(entries) - 1:
                x += gap_between_entries

        return np.array(pil_img)
        
    def create_diagnostic_collage(
        self,
        image_rgb: np.ndarray,
        yolo_obb_results: List[Any],
        yolo_vbb_results: List[Any],
        gt_instances: List[np.ndarray],
        sam_masks: List[np.ndarray],
        detection_outcomes: List[str],
        metadata: Dict[str, Any]
    ) -> np.ndarray:
        """
        Create complete diagnostic collage with 2x2 layout.
        
        Args:
            image_rgb: Original RGB image
            yolo_obb_results: OBB detection results
            yolo_vbb_results: VBB detection results  
            gt_instances: List of GT instance masks
            sam_masks: List of SAM segmentation masks
            detection_outcomes: List of "TP", "FP", or "FN" for each detection
            metadata: Dictionary with image_id, class_name, metrics, etc.
            
        Returns:
            Complete collage image
        """
        # Create 4 panels
        panel_obb = self._create_obb_panel(image_rgb, yolo_obb_results, detection_outcomes)
        panel_vbb = self._create_vbb_panel(image_rgb, yolo_vbb_results, detection_outcomes)
        panel_gt = self._create_gt_panel(image_rgb, gt_instances)
        panel_seg = self._create_seg_panel(image_rgb, sam_masks, detection_outcomes, metadata)
        
        # Arrange in 2x2 grid with spacing
        top_row = self._hstack_with_spacing([panel_obb, panel_vbb])
        bottom_row = self._hstack_with_spacing([panel_gt, panel_seg])
        grid = self._vstack_with_spacing([top_row, bottom_row])
        
        # Create title bar
        title_bar = self._create_title_bar(grid.shape[1], metadata, detection_outcomes)
        
        # Combine title and grid
        collage = np.vstack([title_bar, grid])
        
        return collage
    
    def _create_obb_panel(
        self,
        image: np.ndarray,
        detections: List[Any],
        outcomes: List[str]
    ) -> np.ndarray:
        """Create top-left panel: OBB detections with color-coded boxes."""
        # Resize image to panel size
        panel = cv2.resize(image.copy(), (self.panel_size, self.panel_size))
        
        # Draw oriented bounding boxes
        for det, outcome in zip(detections, outcomes):
            color = self.COLORS.get(outcome, (128, 128, 128))
            self._draw_obb(panel, det, color, orig_shape=image.shape[:2])
        
        # Add panel title with outcome split
        tp = outcomes.count('TP')
        fp = outcomes.count('FP')
        fn = int(0)
        all_count = tp + fp + fn
        title = f"OBB Detections (All: {all_count} | TP: {tp} | FP: {fp} | FN: {fn})"
        panel = self._add_panel_title(panel, title)
        
        # Add outcome counts at bottom
        counts = self._format_outcome_counts(outcomes)
        panel = self._add_panel_footer(panel, counts)
        
        return panel
    
    def _create_vbb_panel(
        self,
        image: np.ndarray,
        detections: List[Any],
        outcomes: List[str]
    ) -> np.ndarray:
        """Create top-right panel: VBB prompts with color-coded boxes."""
        panel = cv2.resize(image.copy(), (self.panel_size, self.panel_size))
        
        # Draw vertical bounding boxes
        for det, outcome in zip(detections, outcomes):
            color = self.COLORS.get(outcome, (128, 128, 128))
            self._draw_vbb(panel, det, color, orig_shape=image.shape[:2])
        
        # Add panel title with outcome split
        tp = outcomes.count('TP')
        fp = outcomes.count('FP')
        fn = int(0)
        all_count = tp + fp + fn
        title = f"VBB Segm. Prompts (All: {all_count} | TP: {tp} | FP: {fp} | FN: {fn})"
        panel = self._add_panel_title(panel, title)
        
        # Add outcome counts at bottom
        counts = self._format_outcome_counts(outcomes)
        panel = self._add_panel_footer(panel, counts)
        
        return panel
    
    def _create_gt_panel(
        self,
        image: np.ndarray,
        gt_instances: List[np.ndarray]
    ) -> np.ndarray:
        """Create bottom-left panel: GT masks in green."""
        panel = cv2.resize(image.copy(), (self.panel_size, self.panel_size))
        
        # Overlay all GT masks in green
        for mask in gt_instances:
            mask_resized = cv2.resize(mask.astype(np.uint8), (self.panel_size, self.panel_size))
            panel = self._overlay_mask(panel, mask_resized, self.COLORS['GT'], alpha=0.4)
        
        # Add panel title
        title = f"Ground Truth Masks ({len(gt_instances)})"
        panel = self._add_panel_title(panel, title)
        
        # Add source info at bottom
        panel = self._add_panel_footer(panel, "From AerialFuseCV semantic masks")
        
        return panel
    
    def _create_seg_panel(
        self,
        image: np.ndarray,
        sam_masks: List[np.ndarray],
        outcomes: List[str],
        metadata: Dict[str, Any],
    ) -> np.ndarray:
        """Create bottom-right panel: Segmented masks in red."""
        panel = cv2.resize(image.copy(), (self.panel_size, self.panel_size))
        
        # Overlay all SAM masks in red
        for mask in sam_masks:
            mask_resized = cv2.resize(mask.astype(np.uint8), (self.panel_size, self.panel_size))
            panel = self._overlay_mask(panel, mask_resized, self.COLORS['SEG'], alpha=0.4)
        
        # Add panel title (Option 1): show all masks and TP/FP split
        all_count = int(metadata.get('det_count', len(sam_masks)))
        tp_count = int(metadata.get('tp_count', outcomes.count('TP')))
        fp_count = int(metadata.get('fp_count', outcomes.count('FP')))
        title = f"Predicted Masks (All:{all_count} | TP:{tp_count} | FP:{fp_count})"
        panel = self._add_panel_title(panel, title)
        
        # Add source info at bottom
        panel = self._add_panel_footer(panel, "From SAM predictions")
        
        return panel
    
    def _create_title_bar(
        self,
        width: int,
        metadata: Dict[str, Any],
        outcomes: List[str]
    ) -> np.ndarray:
        """
        Create centered title bar with 4 lines of information + Detection Legend.
        
        Lines:
        1. Image ID | GSD | Class
        2. GT Instances | Detections | TP | FP | FN
        3. Detected | Recall | Precision | F1
        4. Segmented | Avg IoU | Avg DICE
        5. Detection Legend: 🟢 TP | 🔴 FP | 🟡 FN
        """
        # Title bar dimensions
        line_height = 36
        num_lines = 5  # 4 info lines + 1 legend line
        height = line_height * num_lines + 50  # Extra padding
        
        # Create white background
        title_bar = np.ones((height, width, 3), dtype=np.uint8) * 255
        
        color = (0, 0, 0)  # Black text
        
        # Calculate counts (detections are TP+FP; FN comes from metadata)
        tp_count = int(metadata.get('tp_count', outcomes.count('TP')))
        fp_count = int(metadata.get('fp_count', outcomes.count('FP')))
        fn_count = int(metadata.get('fn_count', metadata.get('gt_count', 0) - tp_count))
        det_count = int(metadata.get('det_count', tp_count + fp_count))
        
        # Line 1: Image ID | GSD | Class
        line1 = f"{metadata.get('image_id', 'N/A')} | GSD = {metadata.get('gsd', 'N/A')}m/px | Class: {metadata.get('class_name', 'N/A')}"
        
        # Line 2: Detection metrics
        recall = metadata.get('recall', 0) * 100
        precision = metadata.get('precision', 0) * 100
        f1 = metadata.get('f1', 0) * 100
        line2 = f"Detection metrics (micro): Recall: {recall:.2f}% | Precision: {precision:.2f}% | F1: {f1:.2f}%"
        
        # Line 3: Conditional segmentation metrics (TP-only)
        avg_iou = metadata.get('avg_iou', 0) * 100
        avg_dice = metadata.get('avg_dice', 0) * 100
        line3 = f"Conditional Segmentation metrics (on TP only): Avg. IoU: {avg_iou:.2f}% | Avg. DICE: {avg_dice:.2f}%"

        # Line 4: End-to-end segmentation metrics (all predictions)
        avg_iou_e2e = metadata.get('avg_iou_e2e', 0) * 100
        avg_dice_e2e = metadata.get('avg_dice_e2e', 0) * 100
        line4 = f"End-to-End Segmentation metrics (on all predictions): Avg. IoU: {avg_iou_e2e:.2f}% | Avg. DICE: {avg_dice_e2e:.2f}%"
        
        # Draw centered text
        y_offset = 30
        for i, line in enumerate([line1, line2, line3, line4]):
            y = y_offset + i * line_height
            title_bar = self._draw_centered_tnr_text(
                title_bar,
                line,
                y=y,
                font_size=24,
                bold=True,
                color=color,
            )

        title_bar = self._draw_detection_legend(title_bar, y=y_offset + 4 * line_height)
        
        return title_bar
    
    def _draw_obb(self, image: np.ndarray, detection: Any, color: Tuple[int, int, int], orig_shape: Tuple[int, int]):
        """Draw oriented bounding box."""
        # Assuming detection has .obb attribute with rotated box points
        if hasattr(detection, 'obb') and detection.obb is not None:
            # Get the 4 corner points of the OBB
            points = detection.obb.xyxyxyxy[0].cpu().numpy() if hasattr(detection.obb, 'xyxyxyxy') else None
            if points is not None:
                # Scale points from original image coordinates to panel coordinates
                orig_h, orig_w = orig_shape
                panel_h, panel_w = image.shape[:2]
                scale_x = panel_w / max(orig_w, 1)
                scale_y = panel_h / max(orig_h, 1)
                points_scaled = points.copy()
                points_scaled[:, 0] *= scale_x
                points_scaled[:, 1] *= scale_y
                points_scaled = points_scaled.astype(np.int32)
                
                # Draw filled polygon with transparency
                overlay = image.copy()
                cv2.fillPoly(overlay, [points_scaled], color)
                cv2.addWeighted(overlay, 0.2, image, 0.8, 0, image)
                
                # Draw bold edge
                cv2.polylines(image, [points_scaled], True, color, 3)
    
    def _draw_vbb(self, image: np.ndarray, detection: Any, color: Tuple[int, int, int], orig_shape: Tuple[int, int]):
        """Draw vertical (axis-aligned) bounding box."""
        if hasattr(detection, 'xyxy'):
            box = detection.xyxy[0].cpu().numpy() if hasattr(detection.xyxy[0], 'cpu') else detection.xyxy[0]
            x1, y1, x2, y2 = box.astype(float)

            # Scale from original image coordinates to panel coordinates
            orig_h, orig_w = orig_shape
            panel_h, panel_w = image.shape[:2]
            sx = panel_w / max(orig_w, 1)
            sy = panel_h / max(orig_h, 1)
            x1, y1, x2, y2 = int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy)
            
            # Draw filled rectangle with transparency
            overlay = image.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
            cv2.addWeighted(overlay, 0.2, image, 0.8, 0, image)
            
            # Draw bold edge
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 3)
    
    def _overlay_mask(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        color: Tuple[int, int, int],
        alpha: float = 0.4
    ) -> np.ndarray:
        """Overlay a mask on an image with transparency."""
        overlay = image.copy()
        overlay[mask > 0] = color
        return cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)
    
    def _add_panel_title(self, panel: np.ndarray, title: str) -> np.ndarray:
        """Add title to top of panel."""
        color = (255, 255, 255)  # White text
        bg_color = (0, 0, 0)  # Black background

        pil_tmp = Image.new("RGB", (10, 10), (0, 0, 0))
        draw_tmp = ImageDraw.Draw(pil_tmp)
        font = self._get_tnr_font(32, bold=True)
        text_bbox = draw_tmp.textbbox((0, 0), title, font=font)
        text_h = text_bbox[3] - text_bbox[1]
        
        # Draw black background rectangle
        cv2.rectangle(panel, (0, 0), (panel.shape[1], text_h + 24), bg_color, -1)

        panel = self._draw_centered_tnr_text(
            panel,
            title,
            y=10,
            font_size=32,
            bold=True,
            color=color,
        )
        
        return panel
    
    def _add_panel_footer(self, panel: np.ndarray, text: str) -> np.ndarray:
        """Add footer text to bottom of panel."""
        color = (255, 255, 255)  # White text
        bg_color = (0, 0, 0)  # Black background

        pil_tmp = Image.new("RGB", (10, 10), (0, 0, 0))
        draw_tmp = ImageDraw.Draw(pil_tmp)
        font = self._get_tnr_font(24, bold=False)
        text_bbox = draw_tmp.textbbox((0, 0), text, font=font)
        text_h = text_bbox[3] - text_bbox[1]
        
        # Draw black background rectangle at bottom
        y_start = panel.shape[0] - text_h - 18
        cv2.rectangle(panel, (0, y_start), (panel.shape[1], panel.shape[0]), bg_color, -1)

        panel = self._draw_centered_tnr_text(
            panel,
            text,
            y=y_start + 4,
            font_size=24,
            bold=False,
            color=color,
        )
        
        return panel
    
    def _format_outcome_counts(self, outcomes: List[str]) -> str:
        """Format outcome counts as string."""
        tp = outcomes.count('TP')
        fp = outcomes.count('FP')
        fn = outcomes.count('FN')
        return f"TP:{tp} | FP:{fp} | FN:{fn}"
    
    def _hstack_with_spacing(self, panels: List[np.ndarray]) -> np.ndarray:
        """Stack panels horizontally with spacing."""
        if len(panels) == 0:
            return np.array([])
        
        height = panels[0].shape[0]
        spacer = np.ones((height, self.spacing, 3), dtype=np.uint8) * 255
        
        result = panels[0]
        for panel in panels[1:]:
            result = np.hstack([result, spacer, panel])
        
        return result
    
    def _vstack_with_spacing(self, rows: List[np.ndarray]) -> np.ndarray:
        """Stack rows vertically with spacing."""
        if len(rows) == 0:
            return np.array([])
        
        width = rows[0].shape[1]
        spacer = np.ones((self.spacing, width, 3), dtype=np.uint8) * 255
        
        result = rows[0]
        for row in rows[1:]:
            result = np.vstack([result, spacer, row])
        
        return result
