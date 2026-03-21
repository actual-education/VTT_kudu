import base64
import json
import logging
import re
from pathlib import Path

from openai import AzureOpenAI, OpenAI

from app.config import settings
from app.services.ai_usage import record_completion_usage
from app.mocks.mock_vision import get_mock_vision_analysis

logger = logging.getLogger(__name__)


class VisionService:
    def __init__(self):
        self._client = None
        self._model = ""

    def analyze_frame(self, frame_path: str, timestamp: float) -> dict:
        """Classify frame visual content. Returns dict with has_text, has_diagram, has_equation, likely_essential, description, confidence."""
        if settings.USE_MOCKS:
            return get_mock_vision_analysis(frame_path, timestamp)
        heuristic = self._heuristic_analysis(frame_path, timestamp)
        client, model = self._get_client()
        if not client or not model:
            if settings.REQUIRE_MODEL_SUCCESS:
                raise RuntimeError(
                    "Vision model is required but no OpenAI/Azure OpenAI client is configured."
                )
            return heuristic

        try:
            ai_result = self._analyze_with_model(client, model, frame_path)
            merged = {**heuristic, **ai_result}
            merged["timestamp"] = timestamp
            return merged
        except Exception as exc:
            if settings.REQUIRE_MODEL_SUCCESS:
                raise RuntimeError(f"Vision model inference failed: {exc}") from exc
            logger.warning("Vision model inference failed, falling back to heuristic analysis: %s", exc)
            return heuristic

    def _heuristic_analysis(self, frame_path: str, timestamp: float) -> dict:
        from app.services.ocr_service import ocr_service

        ocr_text = ocr_service.extract_text(frame_path, timestamp)
        normalized = ocr_text.lower()
        has_text = bool(ocr_text)
        has_equation = bool(re.search(r"=|[+\-*/^]|\b(sigma|integral|sqrt|theta|pi)\b", normalized))
        has_diagram = bool(
            re.search(r"\b(diagram|figure|chart|graph|flow|process|architecture|arrow|matrix)\b", normalized)
        )
        likely_essential = has_equation or has_diagram or (has_text and len(ocr_text) > 20)
        short_text = (ocr_text[:140] + "...") if len(ocr_text) > 140 else ocr_text
        description = "Frame contains visual instructional content"
        if has_text:
            description = f"Frame text: {short_text}"

        return {
            "timestamp": timestamp,
            "has_text": has_text,
            "has_diagram": has_diagram,
            "has_equation": has_equation,
            "likely_essential": likely_essential,
            "ocr_text": ocr_text,
            "description": description,
            "confidence": 0.6,
        }

    def _analyze_with_model(self, client, model: str, frame_path: str) -> dict:
        image_path = Path(frame_path)
        encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{encoded}"
        prompt = (
            "Analyze this educational video frame and return strict JSON with keys: "
            "has_text (bool), has_diagram (bool), has_equation (bool), likely_essential (bool), "
            "ocr_text (string), description (string), confidence (number 0-1)."
        )

        completion = client.chat.completions.create(
            model=model,
            timeout=settings.MODEL_REQUEST_TIMEOUT_SECONDS,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are an accessibility analysis assistant."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
        )
        record_completion_usage(model=model, usage_obj=getattr(completion, "usage", None))
        raw = completion.choices[0].message.content or "{}"
        parsed = json.loads(raw)
        return {
            "has_text": bool(parsed.get("has_text", False)),
            "has_diagram": bool(parsed.get("has_diagram", False)),
            "has_equation": bool(parsed.get("has_equation", False)),
            "likely_essential": bool(parsed.get("likely_essential", False)),
            "ocr_text": str(parsed.get("ocr_text", "") or ""),
            "description": str(parsed.get("description", "") or ""),
            "confidence": float(parsed.get("confidence", 0.6)),
        }

    def _get_client(self):
        if self._client:
            return self._client, self._model

        if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_DEPLOYMENT:
            endpoint = self._normalize_azure_endpoint(settings.AZURE_OPENAI_ENDPOINT)
            self._client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                timeout=settings.MODEL_REQUEST_TIMEOUT_SECONDS,
                max_retries=settings.MODEL_MAX_RETRIES,
            )
            self._model = settings.AZURE_OPENAI_DEPLOYMENT
            return self._client, self._model

        if settings.OPENAI_API_KEY:
            kwargs = {
                "api_key": settings.OPENAI_API_KEY,
                "timeout": settings.MODEL_REQUEST_TIMEOUT_SECONDS,
                "max_retries": settings.MODEL_MAX_RETRIES,
            }
            if settings.OPENAI_BASE_URL:
                kwargs["base_url"] = settings.OPENAI_BASE_URL
            self._client = OpenAI(**kwargs)
            self._model = settings.OPENAI_MODEL
            return self._client, self._model

        return None, ""

    def _normalize_azure_endpoint(self, endpoint: str) -> str:
        marker = "/openai/"
        if marker in endpoint:
            return endpoint.split(marker, 1)[0].rstrip("/")
        return endpoint.rstrip("/")


vision_service = VisionService()
