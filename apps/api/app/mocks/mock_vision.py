import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def get_mock_frame_analyses(video_id: str) -> list[dict]:
    with open(FIXTURES_DIR / "frame_analyses.json") as f:
        return json.load(f)


def get_mock_vision_analysis(frame_path: str, timestamp: float) -> dict:
    analyses = get_mock_frame_analyses("")
    for a in analyses:
        if abs(a["timestamp"] - timestamp) < 10:
            return a
    return {
        "timestamp": timestamp,
        "has_text": False,
        "has_diagram": False,
        "has_equation": False,
        "likely_essential": False,
        "ocr_text": "",
        "description": "General scene with instructor.",
        "confidence": 0.80,
    }
