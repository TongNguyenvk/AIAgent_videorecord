"""
EasyOCR-based text detection for finding UI elements by text content.
This reduces Vision AI calls by first attempting OCR-based element location.
"""
import easyocr
import numpy as np
from PIL import Image
import io
import base64
from typing import Optional
from dataclasses import dataclass


@dataclass
class OCRResult:
    """Result from OCR text detection."""
    text: str
    x: int  # Center X
    y: int  # Center Y
    confidence: float
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)


# Lazy-loaded EasyOCR reader (downloads models on first use)
_reader: Optional[easyocr.Reader] = None


def _get_reader() -> easyocr.Reader:
    """Get or create the EasyOCR reader (lazy initialization)."""
    global _reader
    if _reader is None:
        # Support Vietnamese and English
        _reader = easyocr.Reader(['vi', 'en'], gpu=False, verbose=False)
    return _reader


def detect_text_regions(image_b64: str) -> list[OCRResult]:
    """
    Detect all text regions in an image using EasyOCR.
    
    Args:
        image_b64: Base64-encoded PNG/JPEG image.
        
    Returns:
        List of OCRResult with text, coordinates, and confidence.
    """
    # Decode base64 image
    image_data = base64.b64decode(image_b64)
    image = Image.open(io.BytesIO(image_data))
    image_np = np.array(image)
    
    reader = _get_reader()
    results = reader.readtext(image_np)
    
    ocr_results = []
    for bbox, text, confidence in results:
        # bbox is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
        x1 = int(min(p[0] for p in bbox))
        y1 = int(min(p[1] for p in bbox))
        x2 = int(max(p[0] for p in bbox))
        y2 = int(max(p[1] for p in bbox))
        
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        
        ocr_results.append(OCRResult(
            text=text,
            x=center_x,
            y=center_y,
            confidence=confidence,
            bbox=(x1, y1, x2, y2),
        ))
    
    return ocr_results


def find_text_coordinates(
    image_b64: str,
    target_text: str,
    min_confidence: float = 0.5,
) -> Optional[OCRResult]:
    """
    Find coordinates of text matching the target string.
    
    Uses fuzzy matching to find the best match.
    
    Args:
        image_b64: Base64-encoded screenshot.
        target_text: Text to search for (can be partial match).
        min_confidence: Minimum OCR confidence to consider.
        
    Returns:
        OCRResult if found, None otherwise.
    """
    target_lower = target_text.lower().strip()
    results = detect_text_regions(image_b64)
    
    best_match: Optional[OCRResult] = None
    best_score = 0.0
    
    for result in results:
        if result.confidence < min_confidence:
            continue
            
        detected_lower = result.text.lower().strip()
        
        # Exact match
        if detected_lower == target_lower:
            return result
        
        # Partial match scoring
        score = 0.0
        if target_lower in detected_lower:
            score = len(target_lower) / len(detected_lower) * result.confidence
        elif detected_lower in target_lower:
            score = len(detected_lower) / len(target_lower) * result.confidence
        
        # Word overlap scoring
        target_words = set(target_lower.split())
        detected_words = set(detected_lower.split())
        if target_words & detected_words:
            overlap = len(target_words & detected_words) / len(target_words | detected_words)
            score = max(score, overlap * result.confidence)
        
        if score > best_score:
            best_score = score
            best_match = result
    
    # Return best match if score is good enough
    if best_match and best_score >= 0.3:
        return best_match
    
    return None


def find_button_or_link(
    image_b64: str,
    button_text: str,
) -> Optional[OCRResult]:
    """
    Find a button or link containing the specified text.
    
    Searches for common button patterns like "Sign in", "Submit", etc.
    
    Args:
        image_b64: Base64-encoded screenshot.
        button_text: Button/link text to find.
        
    Returns:
        OCRResult if found, None otherwise.
    """
    # Common button text variations
    variations = [
        button_text,
        button_text.title(),
        button_text.upper(),
        button_text.lower(),
    ]
    
    for variant in variations:
        result = find_text_coordinates(image_b64, variant, min_confidence=0.6)
        if result:
            return result
    
    return None


def find_input_label(
    image_b64: str,
    label_text: str,
    offset_y: int = 30,
) -> Optional[tuple[int, int]]:
    """
    Find an input field by its label text.
    
    Assumes the input is below or to the right of the label.
    
    Args:
        image_b64: Base64-encoded screenshot.
        label_text: Label text (e.g., "Username", "Password").
        offset_y: Pixels to offset down from label to find input.
        
    Returns:
        (x, y) coordinates for the input field, or None.
    """
    result = find_text_coordinates(image_b64, label_text)
    if result:
        # Input is typically below or to the right of label
        return (result.x + 50, result.y + offset_y)
    return None
