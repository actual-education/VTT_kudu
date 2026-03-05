import re
from dataclasses import dataclass


@dataclass
class VttCue:
    start_time: float
    end_time: float
    text: str
    identifier: str | None = None


def parse_vtt_timestamp(ts: str) -> float:
    ts = ts.strip()
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, rest = parts
        s, ms = rest.split(".") if "." in rest else (rest, "0")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000
    if len(parts) == 2:
        m, rest = parts
        s, ms = rest.split(".") if "." in rest else (rest, "0")
        return int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000
    raise ValueError(f"Invalid VTT timestamp: {ts}")


def format_vtt_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


TIMESTAMP_RE = re.compile(
    r"(\d{1,2}:\d{2}:\d{2}\.\d{1,3}|\d{2}:\d{2}\.\d{1,3})"
    r"\s*-->\s*"
    r"(\d{1,2}:\d{2}:\d{2}\.\d{1,3}|\d{2}:\d{2}\.\d{1,3})"
)
INLINE_WORD_TS_RE = re.compile(r"<\d{2}:\d{2}:\d{2}\.\d{1,3}>")
CAPTION_CLASS_TAG_RE = re.compile(r"</?c(?:\.[^>\s]+)?[^>]*>")


def _clean_vtt_text(text: str) -> str:
    cleaned = INLINE_WORD_TS_RE.sub("", text)
    cleaned = CAPTION_CLASS_TAG_RE.sub("", cleaned)
    # Normalize whitespace around removed inline tags.
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def parse_vtt(content: str) -> list[VttCue]:
    lines = content.replace("\r\n", "\n").split("\n")
    cues: list[VttCue] = []
    i = 0

    # Skip WEBVTT header and any metadata
    while i < len(lines):
        if TIMESTAMP_RE.search(lines[i]):
            break
        i += 1

    while i < len(lines):
        line = lines[i].strip()

        # Check if this line is a timestamp line
        match = TIMESTAMP_RE.search(line)
        if match:
            start = parse_vtt_timestamp(match.group(1))
            end = parse_vtt_timestamp(match.group(2))

            # Check if previous non-empty line was an identifier
            identifier = None
            if i > 0 and lines[i - 1].strip() and not TIMESTAMP_RE.search(lines[i - 1]):
                identifier = lines[i - 1].strip()

            # Collect text lines until empty line or next cue
            i += 1
            text_lines: list[str] = []
            while i < len(lines) and lines[i].strip() != "":
                if TIMESTAMP_RE.search(lines[i]):
                    break
                text_lines.append(lines[i].strip())
                i += 1

            text = "\n".join(text_lines)
            text = _clean_vtt_text(text)
            if text:
                cues.append(VttCue(
                    start_time=start,
                    end_time=end,
                    text=text,
                    identifier=identifier,
                ))
        else:
            i += 1

    return cues


def generate_vtt(cues: list[VttCue]) -> str:
    lines = ["WEBVTT", ""]
    for cue in cues:
        if cue.identifier:
            lines.append(cue.identifier)
        lines.append(f"{format_vtt_timestamp(cue.start_time)} --> {format_vtt_timestamp(cue.end_time)}")
        lines.append(cue.text)
        lines.append("")
    return "\n".join(lines)


def validate_vtt(cues: list[VttCue]) -> list[str]:
    errors: list[str] = []

    for i, cue in enumerate(cues):
        # Check for negative or zero duration
        if cue.end_time <= cue.start_time:
            errors.append(f"Cue {i}: end_time ({cue.end_time}) <= start_time ({cue.start_time})")

        # Check for empty text
        if not cue.text.strip():
            errors.append(f"Cue {i}: empty text")

        # Check monotonic start times
        if i > 0 and cue.start_time < cues[i - 1].start_time:
            errors.append(
                f"Cue {i}: start_time ({cue.start_time}) < previous start_time ({cues[i - 1].start_time})"
            )

        # Check for overlapping cues
        if i > 0 and cue.start_time < cues[i - 1].end_time:
            errors.append(
                f"Cue {i}: overlaps with previous cue "
                f"({cue.start_time} < {cues[i - 1].end_time})"
            )

    return errors
