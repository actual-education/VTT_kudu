import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

FIXTURES_DIR = Path(__file__).parent / "fixtures"
_VIDEO_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def _validate_video_id(candidate: str | None) -> str | None:
    if candidate and _VIDEO_ID_RE.fullmatch(candidate):
        return candidate
    return None


def extract_video_id(url_or_id: str) -> str:
    value = (url_or_id or "").strip()
    if not value:
        raise ValueError("YouTube URL is empty")

    direct = _validate_video_id(value)
    if direct:
        return direct

    parsed = urlparse(value)
    host = parsed.netloc.lower().split(":")[0]
    path_parts = [part for part in parsed.path.split("/") if part]

    candidate = None
    if host.endswith("youtu.be"):
        candidate = path_parts[0] if path_parts else None
    elif "youtube" in host:
        qs = parse_qs(parsed.query)
        candidate = qs.get("v", [None])[0]
        if not candidate and len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "v", "live"}:
            candidate = path_parts[1]

    validated = _validate_video_id(candidate)
    if validated:
        return validated

    # Backward-compatible fallback for odd inputs that still contain a valid id.
    fallback = re.search(r"(?:v=|/v/|youtu\.be/|/shorts/|/embed/)([a-zA-Z0-9_-]{11})", value)
    if fallback:
        return fallback.group(1)

    raise ValueError(
        "Cannot extract YouTube video ID. Supported formats include "
        "youtube.com/watch?v=..., youtu.be/..., and youtube.com/shorts/..."
    )


def parse_iso8601_duration(duration: str) -> int:
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    return h * 3600 + m * 60 + s


def get_mock_metadata(video_id: str) -> dict:
    with open(FIXTURES_DIR / "metadata.json") as f:
        data = json.load(f)
    data["id"] = video_id
    snippet = data["snippet"]
    duration_str = data["contentDetails"]["duration"]
    return {
        "youtube_id": video_id,
        "title": snippet["title"],
        "channel_title": snippet["channelTitle"],
        "description": snippet["description"],
        "published_at": snippet["publishedAt"],
        "thumbnail_url": snippet["thumbnails"]["high"]["url"],
        "duration_seconds": parse_iso8601_duration(duration_str),
    }


def get_mock_captions(video_id: str) -> str:
    with open(FIXTURES_DIR / "captions.vtt") as f:
        return f.read()
