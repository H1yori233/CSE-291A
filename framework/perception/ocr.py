"""
OCR (Optical Character Recognition) utilities
Supports both Tesseract and PaddleOCR
"""

import os
from typing import List, Dict, Optional, Tuple
from PIL import Image
import pytesseract


class OCREngine:
    """
    Abstract base class for OCR engines.
    """
    
    def extract_text(self, image: Image.Image) -> str:
        """Extract all text from image"""
        raise NotImplementedError
    
    def extract_text_with_boxes(self, image: Image.Image) -> List[Dict]:
        """Extract text with bounding boxes"""
        raise NotImplementedError


class TesseractOCR(OCREngine):
    """
    OCR using Tesseract.
    Fast and reliable for English text.
    """
    
    def __init__(self, lang: str = 'eng'):
        """
        Initialize Tesseract OCR.
        
        Args:
            lang: Language code (e.g., 'eng', 'chi_sim')
        """
        self.lang = lang
        
        # Check if tesseract is available
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            raise RuntimeError(
                f"Tesseract not found. Please install tesseract-ocr.\n"
                f"macOS: brew install tesseract\n"
                f"Ubuntu: sudo apt-get install tesseract-ocr\n"
                f"Error: {e}"
            )
    
    def extract_text(self, image: Image.Image) -> str:
        """
        Extract all text from image.
        
        Args:
            image: PIL Image
            
        Returns:
            Extracted text as a single string
        """
        try:
            text = pytesseract.image_to_string(image, lang=self.lang)
            return text.strip()
        except Exception as e:
            print(f"OCR error: {e}")
            return ""
    
    def extract_text_with_boxes(self, image: Image.Image) -> List[Dict]:
        """
        Extract text with bounding boxes.
        
        Args:
            image: PIL Image
            
        Returns:
            List of dicts with 'text' and 'bbox' keys
            bbox format: (x, y, width, height)
        """
        try:
            # Get detailed OCR data
            data = pytesseract.image_to_data(
                image, 
                lang=self.lang, 
                output_type=pytesseract.Output.DICT
            )
            
            results = []
            n_boxes = len(data['text'])
            
            for i in range(n_boxes):
                text = data['text'][i].strip()
                if text:  # Only include non-empty text
                    conf = float(data['conf'][i])
                    if conf > 0:  # Only include confident detections
                        bbox = (
                            data['left'][i],
                            data['top'][i],
                            data['width'][i],
                            data['height'][i]
                        )
                        results.append({
                            'text': text,
                            'bbox': bbox,
                            'confidence': conf
                        })
            
            return results
        except Exception as e:
            print(f"OCR error: {e}")
            return []


class PaddleOCR_Engine(OCREngine):
    """
    OCR using PaddleOCR.
    Better for multilingual text and complex layouts.
    """
    
    def __init__(self, lang: str = 'en'):
        """
        Initialize PaddleOCR.
        
        Args:
            lang: Language code (e.g., 'en', 'ch')
        """
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                use_angle_cls=True, 
                lang=lang,
                show_log=False
            )
        except ImportError:
            raise RuntimeError(
                "PaddleOCR not installed.\n"
                "Install with: pip install paddleocr\n"
                "Or use Tesseract OCR (default): OCRManager(engine='tesseract')"
            )
    
    def extract_text(self, image: Image.Image) -> str:
        """
        Extract all text from image.
        
        Args:
            image: PIL Image
            
        Returns:
            Extracted text as a single string
        """
        try:
            # Convert PIL Image to numpy array
            import numpy as np
            img_array = np.array(image)
            
            result = self.ocr.ocr(img_array, cls=True)
            
            if result and result[0]:
                texts = [line[1][0] for line in result[0]]
                return '\n'.join(texts)
            return ""
        except Exception as e:
            print(f"PaddleOCR error: {e}")
            return ""
    
    def extract_text_with_boxes(self, image: Image.Image) -> List[Dict]:
        """
        Extract text with bounding boxes.
        
        Args:
            image: PIL Image
            
        Returns:
            List of dicts with 'text' and 'bbox' keys
            bbox format: ((x1,y1), (x2,y2), (x3,y3), (x4,y4))
        """
        try:
            import numpy as np
            img_array = np.array(image)
            
            result = self.ocr.ocr(img_array, cls=True)
            
            results = []
            if result and result[0]:
                for line in result[0]:
                    bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    text = line[1][0]
                    confidence = line[1][1]
                    
                    results.append({
                        'text': text,
                        'bbox': bbox,
                        'confidence': confidence
                    })
            
            return results
        except Exception as e:
            print(f"PaddleOCR error: {e}")
            return []


class OCRManager:
    """
    Manager for OCR operations with fallback support.
    """
    
    def __init__(
        self, 
        engine: str = 'tesseract',
        lang: str = 'eng'
    ):
        """
        Initialize OCR manager.
        
        Args:
            engine: OCR engine to use ('tesseract' or 'paddle')
            lang: Language code
        """
        self.engine_name = engine
        
        if engine == 'tesseract':
            self.engine = TesseractOCR(lang=lang)
        elif engine == 'paddle':
            self.engine = PaddleOCR_Engine(lang='en' if lang == 'eng' else lang)
        else:
            raise ValueError(f"Unknown OCR engine: {engine}")
    
    def process_screenshot(
        self, 
        image: Image.Image,
        include_boxes: bool = True
    ) -> Dict:
        """
        Process a screenshot with OCR.
        
        Args:
            image: PIL Image to process
            include_boxes: Whether to extract bounding boxes
            
        Returns:
            Dict with 'text' and optionally 'regions' keys
        """
        result = {}
        
        # Extract full text
        result['text'] = self.engine.extract_text(image)
        
        # Extract text regions with boxes
        if include_boxes:
            result['regions'] = self.engine.extract_text_with_boxes(image)
        else:
            result['regions'] = []
        
        return result
    
    def find_text(
        self, 
        image: Image.Image,
        search_text: str,
        case_sensitive: bool = False
    ) -> Optional[Tuple[int, int]]:
        """
        Find text on screen and return its center coordinates.
        
        Args:
            image: PIL Image to search
            search_text: Text to find
            case_sensitive: Whether to match case
            
        Returns:
            (x, y) coordinates of text center, or None if not found
        """
        from framework.utils.coords import find_text_location
        
        regions = self.engine.extract_text_with_boxes(image)
        return find_text_location(search_text, regions, case_sensitive)


# Global OCR manager instance
_ocr_manager = None


def get_ocr_manager(engine: str = 'tesseract', lang: str = 'eng') -> OCRManager:
    """
    Get or create global OCR manager.
    
    Args:
        engine: OCR engine to use
        lang: Language code
        
    Returns:
        OCRManager instance
    """
    global _ocr_manager
    if _ocr_manager is None:
        _ocr_manager = OCRManager(engine=engine, lang=lang)
    return _ocr_manager


def extract_text_from_image(image: Image.Image) -> str:
    """
    Convenience function to extract text from image.
    
    Args:
        image: PIL Image
        
    Returns:
        Extracted text
    """
    return get_ocr_manager().process_screenshot(image, include_boxes=False)['text']

