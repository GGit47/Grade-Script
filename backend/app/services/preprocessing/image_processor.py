import os
import shutil
from typing import List, Tuple
from PIL import Image

try:
    import pymupdf as fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz
        PYMUPDF_AVAILABLE = True
    except ImportError:
        PYMUPDF_AVAILABLE = False


try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


def render_pdf_to_images(pdf_path: str, output_dir: str) -> List[str]:
    """
    Renders each page of a PDF into high-resolution JPG images.
    Returns list of saved image paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    image_paths = []

    if PYMUPDF_AVAILABLE:
        doc = fitz.open(pdf_path)
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            # 2x zoom for crisp handwriting OCR (144 dpi)
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            target_path = os.path.join(output_dir, f"page_{page_idx + 1}.jpg")
            pix.save(target_path)
            image_paths.append(target_path)
        doc.close()
    else:
        # Fallback if fitz is not installed yet
        raise RuntimeError("PyMuPDF (fitz) is not installed. Please install PyMuPDF.")

    return image_paths


def preprocess_image(input_path: str, output_path: str) -> str:
    """
    Applies image preprocessing:
    - Grayscale conversion
    - Contrast enhancement (CLAHE)
    - Noise reduction (Bilateral filter or Gaussian blur)
    - Gentle thresholding/deskewing if feasible
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if OPENCV_AVAILABLE:
        img = cv2.imread(input_path)
        if img is None:
            # Fallback to direct copy if cv2 cannot read
            shutil.copyfile(input_path, output_path)
            return output_path

        # 1. Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. Contrast Enhancement (CLAHE - Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast_enhanced = clahe.apply(gray)

        # 3. Denoising
        denoised = cv2.bilateralFilter(contrast_enhanced, d=5, sigmaColor=50, sigmaSpace=50)

        # 4. Save enhanced image
        cv2.imwrite(output_path, denoised)
        return output_path
    else:
        # Fallback using PIL
        with Image.open(input_path) as im:
            gray = im.convert("L")
            gray.save(output_path)
        return output_path


def crop_image_region(image_path: str, output_path: str, bbox: Tuple[float, float, float, float]) -> str:
    """
    Crops a region from the image given normalized [ymin, xmin, ymax, xmax] (0.0 to 1.0).
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with Image.open(image_path) as img:
        width, height = img.size
        ymin, xmin, ymax, xmax = bbox
        
        # Convert normalized to pixel coordinates
        left = max(0, int(xmin * width))
        top = max(0, int(ymin * height))
        right = min(width, int(xmax * width))
        bottom = min(height, int(ymax * height))

        # Ensure valid crop box
        if right <= left or bottom <= top:
            left, top, right, bottom = 0, 0, width, height

        cropped = img.crop((left, top, right, bottom))
        cropped.save(output_path)
    return output_path


def auto_segment_answer_blocks(image_path: str, num_questions: int = 1) -> List[Tuple[float, float, float, float]]:
    """
    Intelligently partitions answer sheet into answer regions.
    Detects blank pages and returns empty list to avoid creating phantom regions.
    Returns list of normalized bboxes [ymin, xmin, ymax, xmax].
    """
    if OPENCV_AVAILABLE and os.path.exists(image_path):
        try:
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                # Check if page is blank
                _, thresh = cv2.threshold(img, 220, 255, cv2.THRESH_BINARY_INV)
                ink_pixels = int(np.sum(thresh > 0))
                total_pixels = img.shape[0] * img.shape[1]
                if ink_pixels < (total_pixels * 0.0008):  # less than 0.08% ink -> blank page
                    return []
        except Exception:
            pass

    if num_questions <= 0:
        num_questions = 1

    # Leave margins
    margin_x = 0.04
    margin_y = 0.05
    usable_h = 1.0 - (2 * margin_y)
    block_h = usable_h / num_questions

    bboxes = []
    for i in range(num_questions):
        ymin = margin_y + (i * block_h)
        ymax = min(0.98, ymin + block_h - 0.01)
        xmin = margin_x
        xmax = 1.0 - margin_x
        bboxes.append((round(ymin, 3), round(xmin, 3), round(ymax, 3), round(xmax, 3)))

    return bboxes
