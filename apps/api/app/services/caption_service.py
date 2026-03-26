import re

from sqlalchemy.orm import Session

from app.models.video import Video
from app.models.caption_version import CaptionVersion
from app.utils.vtt_parser import VttCue, parse_vtt, generate_vtt, validate_vtt
from app.utils.srt_parser import parse_srt


class CaptionService:
    _MICRO_CUE_MAX_DURATION_SECONDS = 0.12
    _VISUAL_DESCRIPTION_MERGE_GAP_SECONDS = 0.25

    def ingest(self, content: str, video_id: str, db: Session) -> CaptionVersion:
        """Parse raw caption content (VTT or SRT) and store as raw_auto version."""
        content_stripped = content.strip()
        if content_stripped.startswith("WEBVTT"):
            cues = parse_vtt(content_stripped)
        else:
            cues = parse_srt(content_stripped)

        vtt_content = generate_vtt(cues)

        # Determine next version number
        max_version = (
            db.query(CaptionVersion.version_number)
            .filter(CaptionVersion.video_id == video_id)
            .order_by(CaptionVersion.version_number.desc())
            .first()
        )
        next_version = (max_version[0] + 1) if max_version else 1

        version = CaptionVersion(
            video_id=video_id,
            version_number=next_version,
            label="raw_auto",
            vtt_content=vtt_content,
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    def enhance(self, video_id: str, db: Session) -> CaptionVersion | None:
        """Enhance the latest caption version: fix casing, punctuation, add non-speech tags."""
        latest = (
            db.query(CaptionVersion)
            .filter(CaptionVersion.video_id == video_id)
            .order_by(CaptionVersion.version_number.desc())
            .first()
        )
        if not latest:
            return None

        cues = parse_vtt(latest.vtt_content)
        enhanced_cues = [self._enhance_cue(cue) for cue in cues]

        vtt_content = generate_vtt(enhanced_cues)

        version = CaptionVersion(
            video_id=video_id,
            version_number=latest.version_number + 1,
            label="enhanced",
            vtt_content=vtt_content,
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    def _enhance_cue(self, cue: VttCue) -> VttCue:
        """Apply basic enhancements to a single cue."""
        text = cue.text

        # Capitalize first letter of sentences
        text = self._fix_sentence_casing(text)

        # Add period at end if missing punctuation
        text = self._fix_trailing_punctuation(text)

        # Add non-speech tags for common patterns
        text = self._add_non_speech_tags(text)

        return VttCue(
            start_time=cue.start_time,
            end_time=cue.end_time,
            text=text,
            identifier=cue.identifier,
        )

    def _fix_sentence_casing(self, text: str) -> str:
        # Capitalize after sentence-ending punctuation or at start
        def capitalize_match(m: re.Match) -> str:
            return m.group(0).upper()

        # Capitalize start of text
        if text and text[0].isalpha():
            text = text[0].upper() + text[1:]

        # Capitalize after . ! ?
        text = re.sub(r"(?<=[.!?]\s)([a-z])", capitalize_match, text)
        return text

    def _fix_trailing_punctuation(self, text: str) -> str:
        stripped = text.rstrip()
        if stripped and stripped[-1] not in ".!?,;:)]\"'":
            return stripped + "."
        return text

    def _add_non_speech_tags(self, text: str) -> str:
        # Detect and tag common non-speech audio cues
        patterns = [
            (r"\b(applause)\b", "[APPLAUSE]"),
            (r"\b(laughter)\b", "[LAUGHTER]"),
            (r"\b(music playing)\b", "[MUSIC]"),
            (r"\b(silence)\b", "[SILENCE]"),
        ]
        for pattern, tag in patterns:
            text = re.sub(pattern, tag, text, flags=re.IGNORECASE)
        return text

    def get_latest_vtt(self, video_id: str, db: Session) -> str | None:
        latest = (
            db.query(CaptionVersion)
            .filter(CaptionVersion.video_id == video_id)
            .order_by(CaptionVersion.version_number.desc())
            .first()
        )
        return latest.vtt_content if latest else None

    def get_original_vtt(self, video_id: str, db: Session) -> str | None:
        source_version = (
            db.query(CaptionVersion)
            .filter(
                CaptionVersion.video_id == video_id,
                CaptionVersion.label == "raw_auto",
            )
            .order_by(CaptionVersion.version_number.desc())
            .first()
        )
        if source_version:
            return self._dedupe_progressive_vtt(source_version.vtt_content)
        source_version = (
            db.query(CaptionVersion)
            .filter(
                CaptionVersion.video_id == video_id,
                CaptionVersion.label == "enhanced",
            )
            .order_by(CaptionVersion.version_number.desc())
            .first()
        )
        if source_version:
            return self._dedupe_progressive_vtt(source_version.vtt_content)
        latest = self.get_latest_vtt(video_id, db)
        return self._dedupe_progressive_vtt(latest) if latest else None

    def get_visual_descriptions_vtt(
        self,
        video_id: str,
        db: Session,
        education_level: str | None = None,
    ) -> str | None:
        from app.models.segment import Segment

        query = (
            db.query(Segment)
            .filter(
                Segment.video_id == video_id,
                Segment.visual_description.isnot(None),
            )
        )
        segments = query.order_by(Segment.start_time).all()
        if education_level:
            segments = [
                segment for segment in segments
                if self._matches_visual_education_level(segment, education_level)
            ]
        if not segments:
            return None

        cues = [
            VttCue(
                start_time=segment.start_time,
                end_time=segment.end_time,
                text=segment.visual_description.strip(),
            )
            for segment in segments
            if (segment.visual_description or "").strip()
        ]
        if not cues:
            return None
        cues = self._merge_adjacent_visual_description_cues(cues)
        return generate_vtt(cues)

    def get_versions(self, video_id: str, db: Session) -> list[CaptionVersion]:
        return (
            db.query(CaptionVersion)
            .filter(CaptionVersion.video_id == video_id)
            .order_by(CaptionVersion.version_number)
            .all()
        )

    def validate(self, vtt_content: str) -> list[str]:
        cues = parse_vtt(vtt_content)
        return validate_vtt(cues)

    def _dedupe_progressive_vtt(self, vtt_content: str) -> str:
        cues = parse_vtt(vtt_content)
        if not cues:
            return vtt_content

        cleaned: list[VttCue] = []
        for cue in cues:
            text = self._normalize_caption_text(cue.text)
            if not text:
                continue

            current = VttCue(
                start_time=cue.start_time,
                end_time=cue.end_time,
                text=text,
                identifier=cue.identifier,
            )

            if not cleaned:
                cleaned.append(current)
                continue

            previous = cleaned[-1]
            current_duration = current.end_time - current.start_time

            if self._is_micro_duplicate(previous.text, current.text, current_duration):
                continue

            trimmed_text = self._trim_repeated_prefix(previous.text, current.text)
            if trimmed_text:
                current.text = trimmed_text

            if current.text == previous.text:
                previous.end_time = max(previous.end_time, current.end_time)
                continue

            cleaned.append(current)

        return generate_vtt(cleaned)

    def _normalize_caption_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines).strip()

    def _matches_visual_education_level(self, segment, education_level: str) -> bool:
        stored_level = (getattr(segment, "education_level", None) or "").lower()
        if education_level != "high":
            return stored_level == education_level

        if stored_level == "high":
            return True

        text = self._normalize_caption_text(getattr(segment, "visual_description", "") or "").lower()
        if not text:
            return False

        strong_keywords = {
            "educational graphic", "diagram", "equation", "formula", "graph", "chart",
            "field", "charge", "capacitor", "conductor", "cross-section", "labeled",
            "label", "arrow", "plate", "surface", "+q", "-q",
        }
        filler_markers = {
            "studio", "shelves", "green background", "green wall", "light bulbs",
            "decorative", "presenter speaking", "speaking directly to the camera",
            "presenter stands", "presenter sits", "person speaking directly",
        }

        strong_match = any(keyword in text for keyword in strong_keywords)
        filler_only = any(marker in text for marker in filler_markers) and not strong_match
        return strong_match and not filler_only

    def _merge_adjacent_visual_description_cues(self, cues: list[VttCue]) -> list[VttCue]:
        if not cues:
            return []

        merged: list[VttCue] = []
        for cue in cues:
            text = self._normalize_caption_text(cue.text)
            if not text:
                continue

            current = VttCue(
                start_time=cue.start_time,
                end_time=cue.end_time,
                text=text,
                identifier=cue.identifier,
            )

            if not merged:
                merged.append(current)
                continue

            previous = merged[-1]
            gap = current.start_time - previous.end_time
            if (
                previous.text == current.text
                and gap <= self._VISUAL_DESCRIPTION_MERGE_GAP_SECONDS
            ):
                previous.end_time = max(previous.end_time, current.end_time)
                continue

            merged.append(current)

        return merged

    def _is_micro_duplicate(self, previous_text: str, current_text: str, duration: float) -> bool:
        if duration > self._MICRO_CUE_MAX_DURATION_SECONDS:
            return False
        prev_words = self._words(previous_text)
        curr_words = self._words(current_text)
        if not prev_words or not curr_words:
            return False
        return self._is_subsequence(curr_words, prev_words)

    def _trim_repeated_prefix(self, previous_text: str, current_text: str) -> str:
        prev_words = self._words(previous_text)
        curr_words = self._words(current_text)
        overlap = self._overlap_word_count(prev_words, curr_words)
        if overlap <= 0:
            return current_text

        trimmed = self._drop_leading_words(current_text, overlap)
        if not trimmed:
            return current_text
        return trimmed

    def _overlap_word_count(self, previous_words: list[str], current_words: list[str]) -> int:
        max_overlap = min(len(previous_words), len(current_words))
        for size in range(max_overlap, 0, -1):
            if previous_words[-size:] == current_words[:size]:
                return size
        return 0

    def _is_subsequence(self, needle: list[str], haystack: list[str]) -> bool:
        if len(needle) > len(haystack):
            return False
        for start in range(len(haystack) - len(needle) + 1):
            if haystack[start:start + len(needle)] == needle:
                return True
        return False

    def _words(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9']+", text.lower())

    def _drop_leading_words(self, text: str, word_count: int) -> str:
        if word_count <= 0:
            return text

        matches = list(re.finditer(r"[A-Za-z0-9']+", text))
        if len(matches) <= word_count:
            return ""

        start_index = matches[word_count].start()
        return text[start_index:].strip()


caption_service = CaptionService()
