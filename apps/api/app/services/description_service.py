import logging
import json
import re
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

    def curate_education_levels(
        self,
        video_id: str,
        db: Session,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> int:
        segments = (
            db.query(Segment)
            .filter(
                Segment.video_id == video_id,
                Segment.visual_description.isnot(None),
            )
            .order_by(Segment.start_time)
            .all()
        )

        if not segments:
            return 0

        if settings.USE_MOCKS:
            return self._apply_education_updates(
                segments,
                self._heuristic_curate_segments(segments),
                db,
                progress_callback,
            )

        client, model = self._get_client()
        if not client or not model:
            if settings.REQUIRE_MODEL_SUCCESS:
                raise RuntimeError(
                    "Education curation model is required but no OpenAI/Azure OpenAI client is configured."
                )
            return self._apply_education_updates(
                segments,
                self._heuristic_curate_segments(segments),
                db,
                progress_callback,
            )

        if len(segments) > settings.EDUCATION_MODEL_MAX_SEGMENTS:
            logger.info(
                "Education curation falling back to heuristic mode for video %s; segment count %s exceeds limit %s",
                video_id,
                len(segments),
                settings.EDUCATION_MODEL_MAX_SEGMENTS,
            )
            return self._apply_education_updates(
                segments,
                self._heuristic_curate_segments(segments),
                db,
                progress_callback,
            )

        payload = [
            {
                "id": segment.id,
                "start_time": round(segment.start_time, 3),
                "end_time": round(segment.end_time, 3),
                "transcript_text": segment.transcript_text or "",
                "ocr_text": segment.ocr_text or "",
                "visual_description": segment.visual_description or "",
                "has_diagram": bool(segment.has_diagram),
                "has_equation": bool(segment.has_equation),
            }
            for segment in segments
        ]

        try:
            completion = client.chat.completions.create(
                model=model,
                timeout=settings.MODEL_REQUEST_TIMEOUT_SECONDS,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are curating educational visual-description cues for an accessibility video pipeline. "
                            "Evaluate the full sequence of transcript text and visual descriptions together. "
                            "Return strict JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "For each segment below, decide whether the visual description is necessary or materially helpful to understanding "
                            "the educational content of the video.\n"
                            "Rules:\n"
                            "1. Return one result for every input id.\n"
                            "2. Use education_level = 'high' whenever the visual would help a learner follow the lesson, explanation, example, or reasoning.\n"
                            "3. Use education_level = 'low' only for visuals that are mostly ambience, presenter-only framing, or non-instructional context.\n"
                            "Example low: 'A presenter stands in a studio set with shelves on both sides...'\n"
                            "Example high: 'A labeled educational graphic showing a sphere covered with evenly distributed dots representing charges...'\n"
                            "4. Rewrite every kept visual_description into one concise sentence, ideally under 18 words.\n"
                            "5. Remove duplicate or near-duplicate descriptions by returning visual_description as null for redundant entries.\n"
                            "6. Omit studio/background filler unless it is educationally necessary; avoid describing shelves, lights, or presenter posture unless instruction depends on it.\n"
                            "7. Prefer marking diagrams, equations, graphs, written examples, object demonstrations, labeled visuals, and meaningful gestures or manipulations as high.\n"
                            "8. Consider transcript_text and the sequence as a whole when deciding importance.\n"
                            "Return JSON in the shape "
                            "{\"segments\":[{\"id\":\"...\",\"education_level\":\"high|low\",\"visual_description\":\"... or null\"}]}\n\n"
                            f"Input segments:\n{json.dumps(payload, ensure_ascii=True)}"
                        ),
                    },
                ],
                response_format={"type": "json_object"},
            )
            record_completion_usage(model=model, usage_obj=getattr(completion, "usage", None))
            content = (completion.choices[0].message.content or "").strip()
            updates = self._parse_education_response(content)
            if not updates:
                raise ValueError("Education curation response was empty.")
            return self._apply_education_updates(segments, updates, db, progress_callback)
        except Exception as exc:
            if settings.REQUIRE_MODEL_SUCCESS:
                raise RuntimeError(f"Education curation inference failed: {exc}") from exc
            logger.warning("Education curation failed, using heuristic fallback: %s", exc)
            return self._apply_education_updates(
                segments,
                self._heuristic_curate_segments(segments),
                db,
                progress_callback,
            )

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

    def _parse_education_response(self, content: str) -> dict[str, dict[str, str | None]]:
        if not content:
            return {}

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, flags=re.DOTALL)
            if not match:
                return {}
            data = json.loads(match.group(0))

        updates: dict[str, dict[str, str | None]] = {}
        for item in data.get("segments", []):
            segment_id = str(item.get("id", "")).strip()
            if not segment_id:
                continue
            level = str(item.get("education_level", "low")).strip().lower()
            if level not in {"high", "low"}:
                level = "low"
            visual_description = item.get("visual_description")
            if isinstance(visual_description, str):
                visual_description = visual_description.strip() or None
            else:
                visual_description = None
            updates[segment_id] = {
                "education_level": level,
                "visual_description": visual_description,
            }
        return updates

    def _apply_education_updates(
        self,
        segments: list[Segment],
        updates: dict[str, dict[str, str | None]],
        db: Session,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> int:
        total = len(segments)
        updated = 0
        for index, segment in enumerate(segments, start=1):
            update = updates.get(segment.id)
            segment.education_level = "low"
            if update:
                visual_description = update.get("visual_description")
                normalized_visual_description = (
                    visual_description.strip() if isinstance(visual_description, str) and visual_description.strip() else None
                )
                segment.visual_description = normalized_visual_description
                proposed_level = str(update.get("education_level") or "low")
                if self._is_educationally_critical(segment, normalized_visual_description):
                    segment.education_level = "high"
                else:
                    segment.education_level = proposed_level
                updated += 1
            elif segment.visual_description:
                segment.visual_description = segment.visual_description.strip() or None
                if self._is_educationally_critical(segment, segment.visual_description):
                    segment.education_level = "high"

            if progress_callback:
                progress_callback(index, total)

        db.commit()
        return updated

    def _heuristic_curate_segments(
        self,
        segments: list[Segment],
    ) -> dict[str, dict[str, str | None]]:
        updates: dict[str, dict[str, str | None]] = {}
        seen_signatures: list[set[str]] = []

        for segment in segments:
            original = (segment.visual_description or "").strip()
            deduped = self._shorten_visual_description(original)
            signature = self._description_signature(original)
            duplicate = bool(signature) and any(
                self._signature_similarity(signature, previous) >= 0.82 for previous in seen_signatures
            )
            if duplicate:
                deduped = None
            elif signature:
                seen_signatures.append(signature)

            education_level = "high" if self._is_educationally_critical(segment, deduped) else "low"
            updates[segment.id] = {
                "education_level": education_level,
                "visual_description": deduped,
            }

        return updates

    def _shorten_visual_description(self, text: str | None) -> str | None:
        if not text:
            return None
        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            return None

        sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", cleaned) if sentence.strip()]
        boilerplate_markers = (
            "talking-head",
            "presenter rather than",
            "without on-screen",
            "studio setting",
        )
        preferred = [
            sentence for sentence in sentences
            if not any(marker in sentence.lower() for marker in boilerplate_markers)
        ]
        chosen = preferred[0] if preferred else sentences[0]

        words = chosen.split()
        if len(words) > 18:
            chosen = " ".join(words[:18]).rstrip(",;:") + "..."
        return chosen

    def _is_educationally_critical(self, segment: Segment, visual_description: str | None) -> bool:
        if not visual_description:
            return False
        context = " ".join(
            filter(
                None,
                [
                    segment.transcript_text,
                    segment.ocr_text,
                    visual_description,
                ],
            )
        ).lower()
        strong_keywords = {
            "equation", "formula", "graph", "chart", "diagram", "table", "axis",
            "matrix", "curve", "slope", "fraction", "plot", "field", "charge",
            "capacitor", "conductor", "circuit", "vector", "label", "labeled",
            "cross-section", "plate", "arrow", "surface", "distribution",
        }
        helpful_keywords = {
            "example", "demonstration", "shows", "illustrates", "compares",
            "points to", "highlights", "writes", "draws", "moves", "rotates",
            "places", "holds", "connects", "measurement", "result",
        }
        filler_markers = {
            "studio", "shelves", "hanging light", "green wall", "decorative",
            "presenter speaking", "speaking to the camera", "talking-head",
            "background", "desk in a studio", "presenter stands", "presenter sits",
            "presenter seated", "wooden shelves", "light bulbs",
        }

        strong_match = any(keyword in context for keyword in strong_keywords)
        helpful_match = any(keyword in context for keyword in helpful_keywords)
        filler_hits = sum(1 for marker in filler_markers if marker in context)
        filler_only = filler_hits > 0 and not (strong_match or helpful_match)

        if segment.has_equation or segment.has_diagram or segment.has_text or strong_match or helpful_match:
            return True

        if filler_only:
            return False

        # Default to high when the visual is not obviously ambience-only.
        return filler_hits < 2 or segment.risk_level in {"high", "medium"}

    def _description_signature(self, text: str) -> set[str]:
        words = re.findall(r"[a-z0-9]+", text.lower())
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to",
            "of", "and", "or", "for", "with", "this", "that", "it",
        }
        return {word for word in words if len(word) > 1 and word not in stop_words}

    def _signature_similarity(self, left: set[str], right: set[str]) -> float:
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        union = left | right
        if not union:
            return 1.0
        return len(left & right) / len(union)


description_service = DescriptionService()
