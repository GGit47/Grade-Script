import os
import torch
from PIL import Image
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class HandwritingRecognizer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HandwritingRecognizer, cls).__new__(cls)
            cls._instance.processor = None
            cls._instance.model = None
            cls._instance.device = "cuda" if torch.cuda.is_available() else "cpu"
            cls._instance._loaded = False
            cls._instance._load_attempted = False
        return cls._instance

    def load_model(self, model_name: str = "microsoft/trocr-base-handwritten"):
        if self._loaded:
            return

        self._load_attempted = True
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            logger.info(f"Loading TrOCR model '{model_name}' on device '{self.device}'...")
            self.processor = TrOCRProcessor.from_pretrained(model_name)
            self.model = VisionEncoderDecoderModel.from_pretrained(model_name).to(self.device)
            self.model.eval()
            self._loaded = True
            logger.info("TrOCR model successfully loaded.")
        except Exception as e:
            logger.warning(f"Could not load Hugging Face TrOCR model: {e}. Fallback mode active.")
            self._loaded = False

    def recognize_crop(self, image_path: str) -> str:
        """
        Runs handwriting recognition on a single image crop.
        If TrOCR is loaded, runs genuine deep learning inference.
        If crop is blank or unreadable, handles gracefully without fabricating answers.
        """
        if not os.path.exists(image_path):
            return ""

        try:
            image = Image.open(image_path).convert("RGB")
            
            # Check for near-blank images
            import numpy as np
            arr = np.array(image.convert("L"))
            if arr.std() < 5.0:  # Very flat/uniform color
                return "[Blank or empty answer region]"

            if not self._loaded and not getattr(self, "_load_attempted", False):
                self.load_model()

            if self._loaded and self.model is not None and self.processor is not None:
                # TrOCR is designed for line-level images. 
                pixel_values = self.processor(image, return_tensors="pt").pixel_values.to(self.device)
                with torch.no_grad():
                    generated_ids = self.model.generate(
                        pixel_values,
                        max_new_tokens=128,
                        num_beams=4,
                        early_stopping=True
                    )
                recognized_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
                return recognized_text.strip()
            else:
                # Do not fabricate answer text when OCR model is not loaded
                return "[Handwriting recognition unavailable: OCR model not loaded]"

        except Exception as e:
            logger.error(f"Inference error recognizing {image_path}: {e}")
            return f"[Error processing handwriting: {str(e)}]"

handwriting_service = HandwritingRecognizer()
