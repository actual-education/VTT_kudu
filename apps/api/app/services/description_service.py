import logging
from collections.abc import Callable

from openai import AzureOpenAI, OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.services.ai_usage import record_completion_usage
from app.models.segment import Segment
from app.models.video import Video

logger = logging.getLogger(__name__)


class DescriptionService:
    def __init__(self):
        self._client = None
        self._model = ""

    def generate_for_segment(self, segment: Segment, template_only: bool = False) -> str | None:
        """Generate an audio description suggestion for a segment with visual content."""
        if settings.USE_MOCKS:
            return self._mock_generate(segment)
        if not self._segment_has_visual_context(segment):
            return None
        if template_only:
            return self._template_generate(segment)

        client, model = self._get_client()
        if not client or not model:
            if settings.REQUIRE_MODEL_SUCCESS:
                raise RuntimeError(
                    "Description model is required but no OpenAI/Azure OpenAI client is configured."
                )
            return self._template_generate(segment)

        try:
            completion = client.chat.completions.create(
                model=model,
                timeout=settings.MODEL_REQUEST_TIMEOUT_SECONDS,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You write concise ADA audio description cue text for captions. "
                            "Output one sentence only, no markdown."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Create a short audio-description sentence for this segment.\n"
                            f"Transcript: {segment.transcript_text or ''}\n"
                            f"OCR text: {segment.ocr_text or ''}\n"
                            f"Visual description: {segment.visual_description or ''}\n"
                            f"Risk reason: {segment.risk_reason or ''}\n"
                            "Keep it factual and under 25 words."
                        ),
                    },
                ],
            )
            record_completion_usage(model=model, usage_obj=getattr(completion, "usage", None))
            content = (completion.choices[0].message.content or "").strip()
            if content:
                return content
        except Exception as exc:
            if settings.REQUIRE_MODEL_SUCCESS:
                raise RuntimeError(f"Description model inference failed: {exc}") from exc
            logger.warning("Description model inference failed, using template fallback: %s", exc)

        return self._template_generate(segment)

    def _mock_generate(self, segment: Segment) -> str | None:
        return self._template_generate(segment)

    def _template_generate(self, segment: Segment) -> str | None:
        parts: list[str] = []

        if segment.has_equation and segment.ocr_text:
            parts.append(f"[On screen: equation reads {segment.ocr_text}]")
        elif segment.has_diagram and segment.visual_description:
            parts.append(f"[Visual: {segment.visual_description}]")
        elif segment.has_text and segment.ocr_text:
            parts.append(f"[On screen: {segment.ocr_text}]")
        elif segment.visual_description:
            parts.append(f"[Visual: {segment.visual_description}]")

        return " ".join(parts) if parts else None

    def _segment_has_visual_context(self, segment: Segment) -> bool:
        return bool(
            segment.has_text
            or segment.has_diagram
            or segment.has_equation
            or segment.ocr_text
            or segment.visual_description
        )

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

    def generate_for_video(
        self,
        video_id: str,
        db: Session,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> int:
        """Generate descriptions for all high/medium risk segments. Returns count updated."""
        segments = (
            db.query(Segment)
            .filter(
                Segment.video_id == video_id,
                Segment.risk_level.in_(["high", "medium"]),
            )
            .order_by(Segment.start_time)
            .all()
        )

        template_only = len(segments) > settings.DESCRIPTION_MODEL_MAX_SEGMENTS
        count = 0
        total = len(segments)
        for index, seg in enumerate(segments, start=1):
            suggestion = self.generate_for_segment(seg, template_only=template_only)
            if suggestion:
                seg.ai_suggestion = suggestion
                count += 1
            db.commit()
            if progress_callback:
                progress_callback(index, total)

        logger.info(
            "Generated %s descriptions for video %s (template_only=%s, total_segments=%s)",
            count,
            video_id,
            template_only,
            total,
        )
        return count

    def generate_caption_draft(self, video_id: str, db: Session) -> str | None:
        """Generate a new VTT caption version that includes AI description cues
        inserted at appropriate timestamps for high/medium risk segments."""
        from app.services.caption_service import caption_service
        from app.utils.vtt_parser import parse_vtt, generate_vtt, VttCue
        from app.models.caption_version import CaptionVersion

        latest_vtt = caption_service.get_latest_vtt(video_id, db)
        if not latest_vtt:
            return None

        cues = parse_vtt(latest_vtt)

        segments = (
            db.query(Segment)
            .filter(
                Segment.video_id == video_id,
                Segment.ai_suggestion.isnot(None),
            )
            .order_by(Segment.start_time)
            .all()
        )

        if not segments:
            return latest_vtt

        # Build a map of segment start times to AI suggestions
        suggestion_map: dict[float, str] = {}
        for seg in segments:
            suggestion_map[seg.start_time] = seg.ai_suggestion

        # Merge AI suggestions into cues
        merged: list[VttCue] = []
        for cue in cues:
            merged.append(cue)
            if cue.start_time in suggestion_map:
                # Append suggestion text to the existing cue
                merged[-1] = VttCue(
                    start_time=cue.start_time,
                    end_time=cue.end_time,
                    text=f"{cue.text}\n{suggestion_map[cue.start_time]}",
                    identifier=cue.identifier,
                )

        new_vtt = generate_vtt(merged)

        # Determine next version number
        max_ver = (
            db.query(CaptionVersion.version_number)
            .filter(CaptionVersion.video_id == video_id)
            .order_by(CaptionVersion.version_number.desc())
            .first()
        )
        next_ver = (max_ver[0] + 1) if max_ver else 1

        version = CaptionVersion(
            video_id=video_id,
            version_number=next_ver,
            label="reviewed",
            vtt_content=new_vtt,
        )
        db.add(version)
        db.commit()

        return new_vtt


description_service = DescriptionService()
