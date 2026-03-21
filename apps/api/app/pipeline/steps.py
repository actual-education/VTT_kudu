import logging
import re
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.models.video import Video
from app.models.segment import Segment
from app.models.frame_analysis import FrameAnalysis
from app.models.caption_version import CaptionVersion
from app.config import settings
from app.services.youtube_service import youtube_service
from app.services.caption_service import caption_service
from app.services.risk_service import risk_service
from app.services.compliance_service import compliance_service as comp_service
from app.services.description_service import description_service
from app.services.frame_service import frame_service
from app.services.ocr_service import ocr_service
from app.services.vision_service import vision_service
from app.utils.vtt_parser import parse_vtt

logger = logging.getLogger(__name__)


def _normalize_visual_text(text: str | None) -> set[str]:
    if not text:
        return set()
    words = re.findall(r"[a-z0-9]+", text.lower())
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "of",
        "and", "or", "for", "with", "this", "that", "it",
    }
    return {w for w in words if len(w) > 1 and w not in stop_words}


def _text_similarity(a: str | None, b: str | None) -> float:
    left = _normalize_visual_text(a)
    right = _normalize_visual_text(b)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 1.0
    return len(left & right) / len(union)


def _merge_text_lines(first: str | None, second: str | None) -> str | None:
    lines: list[tuple[str, str]] = []  # (normalized, original)

    def _normalize_line(line: str) -> str:
        return re.sub(r"\s+", " ", line.strip().lower())

    for chunk in (first, second):
        if not chunk:
            continue
        for line in chunk.splitlines():
            normalized = line.strip()
            if not normalized:
                continue
            key = _normalize_line(normalized)
            replaced = False
            skip = False
            for idx, (existing_key, _) in enumerate(lines):
                # Drop near-duplicate lines where one is a strict extension of the other.
                if key == existing_key or key in existing_key or existing_key in key:
                    if len(key) > len(existing_key):
                        lines[idx] = (key, normalized)
                        replaced = True
                    else:
                        skip = True
                    break
            if not skip and not replaced:
                lines.append((key, normalized))
    return "\n".join(original for _, original in lines) if lines else None


def _has_visual_context(segment: Segment) -> bool:
    return bool(
        segment.has_text
        or segment.has_diagram
        or segment.has_equation
        or segment.ocr_text
        or segment.visual_description
    )


def _can_merge_segments(previous: Segment, current: Segment) -> bool:
    # Keep temporal continuity: only merge adjacent/near-adjacent cues.
    if current.start_time - previous.end_time > settings.SEGMENT_MERGE_MAX_GAP_SECONDS:
        return False

    prev_has_visual = _has_visual_context(previous)
    curr_has_visual = _has_visual_context(current)
    if prev_has_visual != curr_has_visual:
        return False

    # If neither has visual context, collapse contiguous transcript-only cues.
    if not prev_has_visual and not curr_has_visual:
        return True

    # Require same coarse visual flags.
    if (
        previous.has_text != current.has_text
        or previous.has_diagram != current.has_diagram
        or previous.has_equation != current.has_equation
    ):
        return False

    ocr_similarity = _text_similarity(previous.ocr_text, current.ocr_text)
    desc_similarity = _text_similarity(previous.visual_description, current.visual_description)

    # Merge when visual evidence is effectively unchanged.
    return (
        ocr_similarity >= settings.SEGMENT_MERGE_OCR_SIMILARITY_THRESHOLD
        and desc_similarity >= settings.SEGMENT_MERGE_DESCRIPTION_SIMILARITY_THRESHOLD
    )


def step_fetch_metadata(video: Video, db: Session) -> dict:
    """Step 1: Fetch/refresh video metadata."""
    metadata = youtube_service.get_video_metadata(video.youtube_id)
    video.title = metadata["title"]
    video.channel_title = metadata["channel_title"]
    video.duration_seconds = metadata["duration_seconds"]
    video.thumbnail_url = metadata["thumbnail_url"]
    video.description = metadata["description"]
    db.commit()
    return metadata


def step_download_captions(video: Video, db: Session) -> str:
    """Step 2: Download raw captions."""
    raw_vtt = youtube_service.get_captions(video.youtube_id)
    caption_service.ingest(raw_vtt, video.id, db)
    return raw_vtt


def step_enhance_captions(video: Video, db: Session) -> CaptionVersion | None:
    """Step 3: Enhance captions (casing, punctuation, non-speech tags)."""
    return caption_service.enhance(video.id, db)


def step_extract_frames(video: Video, db: Session) -> list[dict]:
    """Step 4: Extract frames at intervals."""
    duration = video.duration_seconds or 120
    return frame_service.extract_frames(video.youtube_id, duration, interval=10.0)


def step_analyze_frames_ocr(video: Video, frames: list[dict], db: Session) -> list[FrameAnalysis]:
    """Step 5: Run OCR on extracted frames."""
    analyses = []
    for frame in frames:
        ocr_text = ocr_service.extract_text(frame["path"], frame["timestamp"])
        fa = FrameAnalysis(
            video_id=video.id,
            timestamp=frame["timestamp"],
            ocr_text=ocr_text if ocr_text else None,
            has_text=bool(ocr_text),
        )
        db.add(fa)
        analyses.append(fa)
    db.commit()
    return analyses


def step_analyze_frames_vision(
    video: Video,
    frames: list[dict],
    analyses: list[FrameAnalysis],
    db: Session,
    progress_callback: Callable[[int, int], None] | None = None,
) -> None:
    """Step 6: Run vision classification on frames."""
    total = len(frames)
    for index, (frame, fa) in enumerate(zip(frames, analyses), start=1):
        vision = vision_service.analyze_frame(frame["path"], frame["timestamp"])
        fa.has_diagram = vision.get("has_diagram", False)
        fa.has_equation = vision.get("has_equation", False)
        fa.likely_essential = vision.get("likely_essential", False)
        fa.description = vision.get("description")
        fa.confidence = vision.get("confidence")
        # Merge OCR: keep existing if vision didn't find text
        if not fa.has_text and vision.get("has_text", False):
            fa.has_text = True
        if vision.get("ocr_text") and not fa.ocr_text:
            fa.ocr_text = vision["ocr_text"]
        if progress_callback:
            progress_callback(index, total)
    db.commit()


def step_align_segments(video: Video, db: Session) -> list[Segment]:
    """Step 7: Create segments by aligning captions with frame analyses."""
    latest_vtt = caption_service.get_latest_vtt(video.id, db)
    if not latest_vtt:
        return []

    cues = parse_vtt(latest_vtt)
    frame_analyses = (
        db.query(FrameAnalysis)
        .filter(FrameAnalysis.video_id == video.id)
        .order_by(FrameAnalysis.timestamp)
        .all()
    )

    # Clear existing segments
    db.query(Segment).filter(Segment.video_id == video.id).delete()

    raw_segments = []
    for cue in cues:
        # Find frame analyses that fall within this cue's time range
        matching_frames = [
            fa for fa in frame_analyses
            if cue.start_time <= fa.timestamp <= cue.end_time
            or (cue.start_time - 5 <= fa.timestamp <= cue.end_time + 5)
        ]

        # Aggregate visual info from matching frames
        has_text = any(fa.has_text for fa in matching_frames)
        has_diagram = any(fa.has_diagram for fa in matching_frames)
        has_equation = any(fa.has_equation for fa in matching_frames)
        ocr_texts = [fa.ocr_text for fa in matching_frames if fa.ocr_text]
        descriptions = [fa.description for fa in matching_frames if fa.description]

        segment = Segment(
            video_id=video.id,
            start_time=cue.start_time,
            end_time=cue.end_time,
            transcript_text=cue.text,
            ocr_text="\n".join(ocr_texts) if ocr_texts else None,
            visual_description="\n".join(descriptions) if descriptions else None,
            has_text=has_text,
            has_diagram=has_diagram,
            has_equation=has_equation,
        )
        raw_segments.append(segment)

    # Collapse consecutive segments where visuals do not materially change.
    merged_segments: list[Segment] = []
    for seg in raw_segments:
        if not merged_segments:
            merged_segments.append(seg)
            continue

        prev = merged_segments[-1]
        if _can_merge_segments(prev, seg):
            prev.end_time = seg.end_time
            prev.transcript_text = _merge_text_lines(prev.transcript_text, seg.transcript_text)
            prev.ocr_text = _merge_text_lines(prev.ocr_text, seg.ocr_text)
            prev.visual_description = _merge_text_lines(prev.visual_description, seg.visual_description)
            prev.has_text = prev.has_text or seg.has_text
            prev.has_diagram = prev.has_diagram or seg.has_diagram
            prev.has_equation = prev.has_equation or seg.has_equation
        else:
            merged_segments.append(seg)

    for segment in merged_segments:
        db.add(segment)

    db.commit()
    return merged_segments


def step_score_risk(video: Video, segments: list[Segment], db: Session) -> None:
    """Step 8: Assign risk levels to segments using the risk service."""
    risk_service.assess_video_segments(video.id, db)


def step_generate_descriptions(video: Video, segments: list[Segment], db: Session) -> None:
    """Step 9: Generate AI descriptions for high/medium risk segments and create caption draft."""
    description_service.generate_for_video(video.id, db)
    description_service.generate_caption_draft(video.id, db)
    # Re-score after suggestions so risks reflect assisted narration coverage.
    risk_service.assess_video_segments(video.id, db)


def step_compute_compliance(video: Video, segments: list[Segment], db: Session) -> float:
    """Step 10: Compute weighted compliance score using the compliance service."""
    breakdown = comp_service.compute_score(video.id, db)
    return breakdown.overall_score


def step_finalize(video: Video, db: Session) -> None:
    """Step 11: Mark video as scanned."""
    video.status = "scanned"
    db.commit()
