import re
from app.utils.vtt_parser import VttCue


SRT_TIMESTAMP_RE = re.compile(
    r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})"
)


def parse_srt_timestamp(ts: str) -> float:
    ts = ts.strip()
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(content: str) -> list[VttCue]:
    blocks = re.split(r"\n\s*\n", content.strip())
    cues: list[VttCue] = []

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue

        # Find the timestamp line
        ts_line_idx = None
        for idx, line in enumerate(lines):
            if SRT_TIMESTAMP_RE.search(line):
                ts_line_idx = idx
                break

        if ts_line_idx is None:
            continue

        match = SRT_TIMESTAMP_RE.search(lines[ts_line_idx])
        if not match:
            continue

        start = parse_srt_timestamp(match.group(1))
        end = parse_srt_timestamp(match.group(2))

        # Identifier is whatever is above the timestamp (usually a number)
        identifier = lines[ts_line_idx - 1].strip() if ts_line_idx > 0 else None

        # Text is everything after the timestamp line
        text_lines = [l.strip() for l in lines[ts_line_idx + 1:] if l.strip()]
        text = "\n".join(text_lines)

        if text:
            cues.append(VttCue(
                start_time=start,
                end_time=end,
                text=text,
                identifier=identifier,
            ))

    return cues


def srt_to_vtt(content: str) -> str:
    from app.utils.vtt_parser import generate_vtt
    cues = parse_srt(content)
    return generate_vtt(cues)
