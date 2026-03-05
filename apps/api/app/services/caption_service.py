import re

from sqlalchemy.orm import Session

from app.models.video import Video
from app.models.caption_version import CaptionVersion
from app.utils.vtt_parser import VttCue, parse_vtt, generate_vtt, validate_vtt
from app.utils.srt_parser import parse_srt


class CaptionService:
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


caption_service = CaptionService()
