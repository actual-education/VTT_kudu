from PIL import Image
import pytesseract

from app.config import settings
from app.mocks.mock_ocr import get_mock_ocr


class OcrService:
    def extract_text(self, frame_path: str, timestamp: float) -> str:
        if settings.USE_MOCKS:
            return get_mock_ocr(frame_path, timestamp)
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        try:
            with Image.open(frame_path) as image:
                text = pytesseract.image_to_string(image, config="--psm 6")
        except pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError(
                f"Tesseract not found at '{settings.TESSERACT_CMD}'. Install it (e.g. `brew install tesseract`)."
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"OCR failed for frame '{frame_path}': {exc}") from exc

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)


ocr_service = OcrService()
